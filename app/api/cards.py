from fastapi import APIRouter, Depends, HTTPException, Query, Path
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional

from .. import crud, schemas, models
from ..database import get_db
from ..utils.activation import auto_activate_if_needed, extract_card_info, query_card_from_api, get_card_transactions

router = APIRouter(prefix="/cards", tags=["cards"])


@router.post("/", response_model=schemas.CardResponse, status_code=201, summary="创建新卡片")
async def create_card(
    card: schemas.CardCreate,
    db: Session = Depends(get_db)
):
    """
    创建一张新的虚拟卡片
    
    - **card_id**: 卡密（必需，格式：mio-xxxxx-xxxxx-xxxxx-xxxxx）
    - **card_nickname**: 卡片昵称（可选）
    - **card_limit**: 额度（可选，默认 0.0）
    - **validity_hours**: 有效期小时数（可选）
    """
    existing_card = crud.get_card_by_id(db, card.card_id)
    if existing_card:
        raise HTTPException(status_code=400, detail="卡密已存在")

    db_card = crud.create_card(db, card)
    return db_card


@router.get("/", response_model=List[schemas.CardResponse], summary="获取卡片列表")
async def list_cards(
    skip: int = Query(0, ge=0, description="跳过的记录数（用于分页）"),
    limit: int = Query(100, ge=1, le=1000, description="返回的记录数（1-1000）"),
    status: Optional[str] = Query(None, description="按状态筛选（active/inactive/expired/not_expired）"),
    search: Optional[str] = Query(None, description="搜索关键词（匹配卡密或卡号）"),
    db: Session = Depends(get_db)
):
    """
    获取卡片列表，支持分页、筛选和搜索
    
    - **skip**: 跳过的记录数，用于分页（默认 0）
    - **limit**: 返回的记录数，范围 1-1000（默认 100）
    - **status**: 按状态筛选，可选值：active（已激活）、inactive（未激活）、expired（已过期）、not_expired（未过期且已激活）
    - **search**: 搜索关键词，会在卡密和卡号中搜索匹配项
    """
    cards = crud.get_cards(db, skip=skip, limit=limit, status=status, search=search)
    return cards


@router.get("/{card_id}", response_model=schemas.CardResponse, summary="获取单个卡片信息")
async def get_card(
    card_id: str = Path(..., description="卡密（格式：mio-xxxxx-xxxxx-xxxxx-xxxxx）"),
    db: Session = Depends(get_db)
):
    """
    根据卡密获取单个卡片的详细信息
    
    - **card_id**: 卡密，格式为 mio-xxxxx-xxxxx-xxxxx-xxxxx
    """
    db_card = crud.get_card_by_id(db, card_id)
    if not db_card:
        raise HTTPException(status_code=404, detail="卡片不存在")
    return db_card


@router.put("/{card_id}", response_model=schemas.CardResponse, summary="更新卡片信息")
async def update_card(
    card_id: str = Path(..., description="卡密"),
    card_update: schemas.CardUpdate = ...,
    db: Session = Depends(get_db)
):
    """
    更新卡片信息（部分更新）
    
    - **card_id**: 卡密
    - **card_update**: 要更新的字段（card_nickname、card_limit、validity_hours、status）
    """
    db_card = crud.update_card(db, card_id, card_update)
    if not db_card:
        raise HTTPException(status_code=404, detail="卡片不存在")
    return db_card


@router.delete("/{card_id}", response_model=schemas.APIResponse, summary="删除卡片")
async def delete_card(
    card_id: str = Path(..., description="卡密"),
    db: Session = Depends(get_db)
):
    """
    删除卡片（软删除，将状态标记为 deleted）
    
    - **card_id**: 卡密
    """
    success = crud.delete_card(db, card_id)
    if not success:
        raise HTTPException(status_code=404, detail="卡片不存在")
    return {"success": True, "message": "卡片已删除"}


@router.post("/{card_id}/activate", response_model=schemas.ActivationResponse, summary="激活卡片")
async def activate_card(
    card_id: str = Path(..., description="卡密"),
    db: Session = Depends(get_db)
):
    """
    激活虚拟卡片
    
    自动执行以下流程：
    1. 从 MisaCard API 查询卡片信息
    2. 如果卡片未激活，自动调用激活 API
    3. 更新本地数据库中的卡片信息（卡号、CVC、有效期等）
    4. 记录激活日志
    
    - **card_id**: 卡密
    """
    db_card = crud.get_card_by_id(db, card_id)
    if not db_card:
        raise HTTPException(status_code=404, detail="卡片不存在于本地数据库")

    success, card_data, message = await auto_activate_if_needed(card_id)

    if not success:
        crud.create_activation_log(db, card_id, "failed", error_message=message)
        raise HTTPException(status_code=400, detail=message)

    card_info = extract_card_info(card_data)

    if card_info.get("card_number"):
        from datetime import datetime
        exp_date = None
        if card_info.get("exp_date"):
            try:
                exp_date = datetime.fromisoformat(card_info["exp_date"].replace('Z', '+00:00'))
            except:
                pass

        crud.activate_card_in_db(
            db,
            card_id,
            card_info["card_number"],
            card_info["card_cvc"],
            card_info["card_exp_date"],
            card_info.get("billing_address"),
            validity_hours=card_info.get("validity_hours"),
            exp_date=exp_date
        )

        crud.create_activation_log(db, card_id, "success")
        db_card = crud.get_card_by_id(db, card_id)
        return {
            "success": True,
            "message": message,
            "card_data": db_card
        }
    else:
        return {
            "success": True,
            "message": message,
            "card_data": db_card
        }


@router.post("/{card_id}/query", response_model=schemas.ActivationResponse, summary="查询并更新卡片信息")
async def query_card(
    card_id: str = Path(..., description="卡密"),
    db: Session = Depends(get_db)
):
    """
    从 MisaCard API 查询卡片信息并更新本地数据库
    
    用于获取最新的卡片状态、过期时间等信息，如果卡片已激活，会更新完整的卡片信息。
    
    - **card_id**: 卡密
    """
    db_card = crud.get_card_by_id(db, card_id)
    if not db_card:
        raise HTTPException(status_code=404, detail="卡片不存在于本地数据库")

    success, card_data, error = await query_card_from_api(card_id)
    if not success:
        raise HTTPException(status_code=400, detail=error or "查询失败")

    card_info = extract_card_info(card_data)

    from datetime import datetime, timezone, timedelta
    exp_date = None
    if card_info.get("exp_date"):
        try:
            dt = datetime.fromisoformat(card_info["exp_date"].replace('Z', '+00:00'))
            if dt.tzinfo is None:
                utc8 = timezone(timedelta(hours=8))
                dt = dt.replace(tzinfo=utc8)
                exp_date = dt.astimezone(timezone.utc)
            else:
                exp_date = dt.astimezone(timezone.utc)
        except:
            pass

    update_data = schemas.CardUpdate(
        card_limit=card_info.get("card_limit"),
        status=card_info.get("status")
    )

    if card_info.get("card_number"):
        crud.activate_card_in_db(
            db,
            card_id,
            str(card_info["card_number"]),
            str(card_info["card_cvc"]),
            card_info["card_exp_date"],
            card_info.get("billing_address"),
            validity_hours=card_info.get("validity_hours"),
            exp_date=exp_date
        )
    else:
        db_card.validity_hours = card_info.get("validity_hours")
        db_card.exp_date = exp_date
        crud.update_card(db, card_id, update_data)

    db_card = crud.get_card_by_id(db, card_id)
    return {
        "success": True,
        "message": "查询成功",
        "card_data": db_card
    }


@router.get("/{card_id}/logs", response_model=List[dict], summary="获取卡片激活历史记录")
async def get_activation_logs(
    card_id: str = Path(..., description="卡密"),
    db: Session = Depends(get_db)
):
    """
    获取指定卡片的激活历史记录
    
    - **card_id**: 卡密
    
    返回激活日志列表，包含每次激活的状态（success/failed）、错误信息、激活时间等。
    """
    logs = crud.get_activation_logs(db, card_id)
    return [
        {
            "id": log.id,
            "status": log.status,
            "error_message": log.error_message,
            "activation_time": log.activation_time,
        }
        for log in logs
    ]


@router.post("/{card_id}/refund", response_model=schemas.APIResponse, summary="切换退款状态")
async def toggle_refund_status(
    card_id: str = Path(..., description="卡密"),
    db: Session = Depends(get_db)
):
    """
    切换卡片的退款申请状态
    
    如果卡片当前未标记为退款，则标记为已申请退款；如果已标记，则取消标记。
    
    - **card_id**: 卡密
    """
    from datetime import datetime

    db_card = crud.get_card_by_id(db, card_id)
    if not db_card:
        raise HTTPException(status_code=404, detail="卡片不存在")

    db_card.refund_requested = not db_card.refund_requested

    if db_card.refund_requested:
        from datetime import timezone
        db_card.refund_requested_time = datetime.now(timezone.utc)
        message = "已标记为申请退款"
    else:
        db_card.refund_requested_time = None
        message = "已取消退款标记"

    db.commit()
    db.refresh(db_card)

    return {
        "success": True,
        "message": message,
        "data": {"refund_requested": db_card.refund_requested}
    }


@router.get("/batch/unreturned-card-numbers", response_model=schemas.APIResponse, summary="获取已过期未退款卡号列表")
async def get_unreturned_card_numbers(
    db: Session = Depends(get_db)
):
    """
    获取所有已过期、未退款且已激活的卡号列表
    
    用于批量复制和申请退款。返回的卡片满足以下条件：
    - 状态为已过期（expired）
    - 已激活（有卡号）
    - 未标记为已申请退款
    
    返回卡号列表和总数。
    """
    crud.update_expired_cards(db)

    cards = db.query(models.Card).filter(
        models.Card.status == 'expired',
        models.Card.is_activated == True,
        models.Card.refund_requested == False,
        models.Card.card_number.isnot(None)
    ).all()

    card_numbers = [str(card.card_number) for card in cards]

    return {
        "success": True,
        "message": f"找到 {len(card_numbers)} 张已过期未退款的卡片",
        "data": {
            "count": len(card_numbers),
            "card_numbers": card_numbers
        }
    }


@router.get("/{card_id}/transactions", response_model=schemas.APIResponse, summary="获取卡片消费记录")
async def get_card_transaction_history(
    card_id: str = Path(..., description="卡密"),
    db: Session = Depends(get_db)
):
    """
    获取指定卡片的消费记录和余额信息
    
    需要卡片已激活（有卡号）才能查询。从 MisaCard API 获取最新的交易记录和余额信息。
    
    - **card_id**: 卡密
    
    返回的数据包括：
    - 余额信息（可用额度、已入账、待处理等）
    - 交易记录列表（金额、状态、时间、描述等）
    """
    db_card = crud.get_card_by_id(db, card_id)
    if not db_card:
        raise HTTPException(status_code=404, detail="卡片不存在")

    if not db_card.card_number:
        raise HTTPException(status_code=400, detail="卡片未激活，无法查询消费记录")

    success, card_info, error = await get_card_transactions(str(db_card.card_number))

    if not success:
        raise HTTPException(status_code=400, detail=error or "查询消费记录失败")

    return {
        "success": True,
        "message": "查询成功",
        "data": card_info
    }
