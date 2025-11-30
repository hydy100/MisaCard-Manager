from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from .. import crud, schemas
from ..database import get_db
from ..utils.parser import parse_txt_file, validate_card_id

router = APIRouter(prefix="/import", tags=["import"])


class TextImportRequest(BaseModel):
    """文本导入请求模型"""
    content: str = Field(..., description="卡片数据文本内容，支持多行，每行一条卡片信息。格式：卡密: mio-xxx 额度: x 有效期: x小时")


@router.post("/text", response_model=schemas.CardImportResponse, summary="从文本批量导入卡片")
async def import_from_text(
    request: TextImportRequest,
    db: Session = Depends(get_db)
):
    """
    从文本内容批量导入卡片（支持剪贴板粘贴）
    
    支持格式：
    - 完整格式：`卡密: mio-xxxxx 额度: 1 有效期: 1小时`
    - 仅卡密：`mio-xxxxx`（使用默认额度 0 和有效期 1 小时）
    
    可以一次导入多行，每行一条卡片信息。
    
    - **content**: 文本内容，支持多行
    
    返回导入结果，包括成功数量、失败数量和失败详情。
    """
    text_content = request.content.strip()

    if not text_content:
        raise HTTPException(status_code=400, detail="文本内容不能为空")

    parsed_cards, failed_lines = parse_txt_file(text_content)

    if not parsed_cards:
        raise HTTPException(
            status_code=400,
            detail=f"没有成功解析任何卡片数据。失败的行: {failed_lines}"
        )

    success_count = 0
    failed_count = 0
    failed_items = []

    for card_data in parsed_cards:
        try:
            if not validate_card_id(card_data["card_id"]):
                failed_count += 1
                failed_items.append({
                    "card_id": card_data["card_id"],
                    "reason": "卡密格式不正确"
                })
                continue

            existing_card = crud.get_card_by_id(db, card_data["card_id"])
            if existing_card:
                failed_count += 1
                failed_items.append({
                    "card_id": card_data["card_id"],
                    "reason": "卡密已存在"
                })
                continue

            card_create = schemas.CardCreate(**card_data)
            crud.create_card(db, card_create)
            success_count += 1

        except Exception as e:
            failed_count += 1
            failed_items.append({
                "card_id": card_data.get("card_id", "未知"),
                "reason": str(e)
            })

    return {
        "success_count": success_count,
        "failed_count": failed_count,
        "failed_items": failed_items,
        "message": f"成功导入 {success_count} 张卡片，失败 {failed_count} 张"
    }


@router.post("/json", response_model=schemas.CardImportResponse, summary="从 JSON 批量导入卡片")
async def import_from_json(
    import_data: schemas.CardImportRequest,
    db: Session = Depends(get_db)
):
    """
    从 JSON 数据批量导入卡片
    
    JSON 格式示例：
    ```json
    {
        "cards": [
            {
                "card_id": "mio-xxxxx-xxxxx-xxxxx-xxxxx",
                "card_limit": 1.0,
                "validity_hours": 1
            }
        ]
    }
    ```
    
    - **cards**: 卡片数组，每个卡片包含 card_id、card_limit、validity_hours
    
    返回导入结果，包括成功数量、失败数量和失败详情。
    """
    success_count = 0
    failed_count = 0
    failed_items = []

    for card_item in import_data.cards:
        try:
            if not validate_card_id(card_item.card_id):
                failed_count += 1
                failed_items.append({
                    "card_id": card_item.card_id,
                    "reason": "卡密格式不正确"
                })
                continue

            existing_card = crud.get_card_by_id(db, card_item.card_id)
            if existing_card:
                failed_count += 1
                failed_items.append({
                    "card_id": card_item.card_id,
                    "reason": "卡密已存在"
                })
                continue

            card_create = schemas.CardCreate(
                card_id=card_item.card_id,
                card_limit=card_item.card_limit,
                validity_hours=card_item.validity_hours
            )
            crud.create_card(db, card_create)
            success_count += 1

        except Exception as e:
            failed_count += 1
            failed_items.append({
                "card_id": card_item.card_id,
                "reason": str(e)
            })

    return {
        "success_count": success_count,
        "failed_count": failed_count,
        "failed_items": failed_items,
        "message": f"成功导入 {success_count} 张卡片，失败 {failed_count} 张"
    }
