"""
数据库 CRUD 操作
"""
from sqlalchemy.orm import Session
from sqlalchemy import or_
from datetime import datetime, timedelta
from typing import Optional
from . import models, schemas


def get_card_by_id(db: Session, card_id: str) -> Optional[models.Card]:
    """根据卡密获取卡片"""
    card = db.query(models.Card).filter(models.Card.card_id == card_id).first()

    # 检查并更新单张卡片的过期状态
    if card and card.exp_date and card.status not in ['deleted', 'expired']:
        from .config import get_current_time
        now = get_current_time()
        exp_date = card.exp_date
        
        # 移除时区信息进行比较
        now_naive = now.replace(tzinfo=None) if now.tzinfo else now
        exp_naive = exp_date.replace(tzinfo=None) if exp_date.tzinfo else exp_date

        if now_naive > exp_naive:
            card.status = 'expired'
            db.commit()
            db.refresh(card)

    return card


def get_cards(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    search: Optional[str] = None
) -> list[models.Card]:
    """获取卡片列表（支持筛选和搜索）"""
    # 先更新所有过期的卡片状态
    update_expired_cards(db)

    query = db.query(models.Card)

    # 状态筛选
    if status:
        query = query.filter(models.Card.status == status)

    # 搜索功能（卡密、昵称、卡号）
    if search:
        query = query.filter(
            or_(
                models.Card.card_id.contains(search),
                models.Card.card_nickname.contains(search),
                models.Card.card_number.contains(search)
            )
        )

    return query.offset(skip).limit(limit).all()


def update_expired_cards(db: Session) -> int:
    """
    检查并更新所有过期的卡片
    返回更新的卡片数量
    """
    from .config import get_current_time
    now = get_current_time()

    # 查找所有未删除且有过期时间的卡片
    cards = db.query(models.Card).filter(
        models.Card.status != 'deleted',
        models.Card.status != 'expired',
        models.Card.exp_date.isnot(None)
    ).all()

    # 更新状态为已过期
    count = 0
    for card in cards:
        exp_date = card.exp_date
        # 移除时区信息进行比较（假设都是同一时区）
        now_naive = now.replace(tzinfo=None) if now.tzinfo else now
        exp_naive = exp_date.replace(tzinfo=None) if exp_date.tzinfo else exp_date

        if now_naive > exp_naive:
            card.status = 'expired'
            count += 1

    if count > 0:
        db.commit()

    return count


def create_card(db: Session, card: schemas.CardCreate) -> models.Card:
    """创建新卡片"""
    # 注意：过期时间(exp_date)应该从API的delete_date字段获取，而不是自己计算
    # 导入时先设为None，等查询/激活后再从API更新
    db_card = models.Card(
        card_id=card.card_id,
        card_nickname=card.card_nickname,
        card_limit=card.card_limit,
        validity_hours=card.validity_hours,
        exp_date=None,  # 不自己计算，等API返回
        status="inactive"
    )
    db.add(db_card)
    db.commit()
    db.refresh(db_card)
    return db_card


def update_card(db: Session, card_id: str, card_update: schemas.CardUpdate) -> Optional[models.Card]:
    """更新卡片信息"""
    db_card = get_card_by_id(db, card_id)
    if not db_card:
        return None

    update_data = card_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_card, field, value)

    db.commit()
    db.refresh(db_card)
    return db_card


def delete_card(db: Session, card_id: str) -> bool:
    """删除卡片（硬删除 - 真正从数据库删除）"""
    db_card = db.query(models.Card).filter(models.Card.card_id == card_id).first()
    if not db_card:
        return False

    db.delete(db_card)
    db.commit()
    return True


def activate_card_in_db(
    db: Session,
    card_id: str,
    card_number: str,
    card_cvc: str,
    card_exp_date: str,
    billing_address: Optional[str] = None,
    validity_hours: Optional[int] = None,
    exp_date: Optional[datetime] = None
) -> Optional[models.Card]:
    """更新卡片激活信息"""
    db_card = get_card_by_id(db, card_id)
    if not db_card:
        return None

    from .config import get_current_time
    db_card.card_number = card_number
    db_card.card_cvc = card_cvc
    db_card.card_exp_date = card_exp_date
    db_card.billing_address = billing_address
    db_card.is_activated = True
    db_card.status = "active"
    db_card.card_activation_time = get_current_time()  # 使用配置的时区

    # 更新有效期小时数和过期时间（从API的delete_date获取）
    if validity_hours is not None:
        db_card.validity_hours = validity_hours
    if exp_date is not None:
        db_card.exp_date = exp_date

    db.commit()
    db.refresh(db_card)
    return db_card


def create_activation_log(
    db: Session,
    card_id: str,
    status: str,
    error_message: Optional[str] = None,
    response_data: Optional[str] = None
) -> models.ActivationLog:
    """创建激活记录"""
    log = models.ActivationLog(
        card_id=card_id,
        status=status,
        error_message=error_message,
        response_data=response_data
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def get_activation_logs(db: Session, card_id: str) -> list[models.ActivationLog]:
    """获取卡片的激活记录"""
    return db.query(models.ActivationLog).filter(
        models.ActivationLog.card_id == card_id
    ).order_by(models.ActivationLog.activation_time.desc()).all()
