"""
Pydantic 数据验证模型
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class CardBase(BaseModel):
    """卡片基础模型"""
    card_id: str = Field(..., description="卡密（格式：mio-xxxxx-xxxxx-xxxxx-xxxxx，必需）")
    card_nickname: Optional[str] = Field(None, description="卡片昵称（可选）")
    card_limit: float = Field(default=0.0, description="额度（美元，默认 0.0）")
    validity_hours: Optional[int] = Field(None, description="有效期（小时数，可选）")


class CardCreate(CardBase):
    """
    创建卡片请求模型
    
    用于创建新的虚拟卡片，需要提供卡密，其他字段可选。
    """
    pass


class CardUpdate(BaseModel):
    """
    更新卡片请求模型
    
    用于部分更新卡片信息，所有字段都是可选的，只更新提供的字段。
    """
    card_nickname: Optional[str] = Field(None, description="卡片昵称（可选）")
    card_limit: Optional[float] = Field(None, description="额度（美元，可选）")
    validity_hours: Optional[int] = Field(None, description="有效期（小时数，可选）")
    status: Optional[str] = Field(None, description="状态（可选值：active/inactive/expired/deleted）")


class CardResponse(CardBase):
    """
    卡片响应模型
    
    返回完整的卡片信息，包括基础信息和激活后的详细信息。
    """
    id: int = Field(..., description="卡片ID（数据库主键）")
    card_number: Optional[str] = Field(None, description="卡号（16位数字，激活后才有）")
    card_cvc: Optional[str] = Field(None, description="CVC（3位数字，激活后才有）")
    card_exp_date: Optional[str] = Field(None, description="信用卡有效期（格式：MM/YY，如 11/31，激活后才有）")
    billing_address: Optional[str] = Field(None, description="账单地址（激活后才有）")
    status: str = Field(..., description="状态（active=已激活可用，inactive=未激活，expired=已过期，deleted=已删除）")
    is_activated: bool = Field(..., description="是否已激活（true=已激活，false=未激活）")
    create_time: datetime = Field(..., description="创建时间（UTC）")
    card_activation_time: Optional[datetime] = Field(None, description="激活时间（UTC，激活后才有）")
    exp_date: Optional[datetime] = Field(None, description="过期时间（UTC）")
    delete_date: Optional[datetime] = Field(None, description="删除时间（UTC，删除后才有）")
    refund_requested: bool = Field(False, description="是否已申请退款（true=已申请，false=未申请）")
    refund_requested_time: Optional[datetime] = Field(None, description="退款申请时间（UTC，申请退款后才有）")

    class Config:
        from_attributes = True


class CardImportItem(BaseModel):
    """
    批量导入单条卡片数据模型
    
    用于 JSON 批量导入，每条卡片需要包含完整信息。
    """
    card_id: str = Field(..., description="卡密（格式：mio-xxxxx-xxxxx-xxxxx-xxxxx，必需）")
    card_limit: float = Field(..., description="额度（美元，必需）")
    validity_hours: int = Field(..., description="有效期（小时数，必需）")


class CardImportRequest(BaseModel):
    """
    批量导入请求模型（JSON 格式）
    
    用于 JSON 批量导入，包含多个卡片信息的数组。
    """
    cards: list[CardImportItem] = Field(..., description="卡片列表（数组，每个元素包含 card_id、card_limit、validity_hours）")


class CardImportResponse(BaseModel):
    """
    批量导入响应模型
    
    返回批量导入的结果，包括成功和失败的数量，以及失败详情。
    """
    success_count: int = Field(..., description="成功导入的卡片数量")
    failed_count: int = Field(..., description="导入失败的卡片数量")
    failed_items: list[dict] = Field(..., description="失败的卡片列表，每个元素包含 card_id（卡密）和 reason（失败原因）")
    message: str = Field(..., description="结果消息（包含成功和失败的数量统计）")


class ActivationRequest(BaseModel):
    """
    激活请求模型
    
    用于激活卡片（当前未使用，激活通过路径参数传递 card_id）。
    """
    card_id: str = Field(..., description="卡密（格式：mio-xxxxx-xxxxx-xxxxx-xxxxx）")


class ActivationResponse(BaseModel):
    """
    激活/查询响应模型
    
    用于激活卡片或查询卡片信息的响应，包含操作结果和卡片数据。
    """
    success: bool = Field(..., description="操作是否成功（true=成功，false=失败）")
    message: str = Field(..., description="响应消息（描述操作结果或错误信息）")
    card_data: Optional[CardResponse] = Field(None, description="卡片数据（操作成功时返回完整的卡片信息）")


class APIResponse(BaseModel):
    """
    通用 API 响应模型
    
    用于各种操作的通用响应格式，包含操作结果、消息和可选的数据。
    """
    success: bool = Field(..., description="操作是否成功（true=成功，false=失败）")
    message: str = Field(..., description="响应消息（描述操作结果或错误信息）")
    data: Optional[dict] = Field(None, description="响应数据（可选，根据不同的接口返回不同的数据结构）")
