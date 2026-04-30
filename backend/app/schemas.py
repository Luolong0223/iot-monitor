"""Pydantic Schemas - 请求/响应数据模型"""
from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime


# ============ 通用响应 ============

class ResponseModel(BaseModel):
    """统一响应格式"""
    code: int = 200
    message: str = "success"
    data: Any = None


class PaginatedResponse(BaseModel):
    """分页响应"""
    code: int = 200
    message: str = "success"
    data: dict = None


# ============ 认证 ============

class LoginRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict


class RefreshRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=6)
    new_password: str = Field(..., min_length=8, max_length=100)


# ============ 层级 ============

class HierarchyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    parent_id: Optional[int] = None
    level_type: str = Field(..., pattern="^(province|city|district|site)$")
    sort_order: int = 0
    description: Optional[str] = None


class HierarchyUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    parent_id: Optional[int] = None
    level_type: Optional[str] = None
    sort_order: Optional[int] = None
    description: Optional[str] = None


class HierarchyResponse(BaseModel):
    id: int
    name: str
    parent_id: Optional[int]
    level_type: str
    sort_order: int
    description: Optional[str]
    created_at: datetime
    children: List["HierarchyResponse"] = []

    class Config:
        from_attributes = True


# ============ 设备 ============

class DeviceCreate(BaseModel):
    device_code: str = Field(..., min_length=1, max_length=100)
    device_name: Optional[str] = Field(None, max_length=200)
    device_type: str = "4g_dtu"
    hierarchy_id: int
    comm_mode: str = "mqtt"
    protocol_id: Optional[int] = None
    sim_card: Optional[str] = None
    install_date: Optional[str] = None
    remark: Optional[str] = None


class DeviceUpdate(BaseModel):
    device_name: Optional[str] = None
    device_type: Optional[str] = None
    hierarchy_id: Optional[int] = None
    comm_mode: Optional[str] = None
    protocol_id: Optional[int] = None
    sim_card: Optional[str] = None
    install_date: Optional[str] = None
    status: Optional[str] = None
    remark: Optional[str] = None


class DeviceResponse(BaseModel):
    id: int
    device_code: str
    device_name: Optional[str]
    device_type: str
    hierarchy_id: Optional[int]
    comm_mode: str
    protocol_id: Optional[int]
    sim_card: Optional[str]
    install_date: Optional[str]
    status: str
    last_heartbeat: Optional[datetime]
    firmware_version: Optional[str]
    remark: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ============ 数据点 ============

class DataItemCreate(BaseModel):
    item_code: str = Field(..., min_length=1, max_length=50)
    item_name: str = Field(..., min_length=1, max_length=100)
    unit: Optional[str] = None
    data_type: str = "float"
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    alarm_enabled: bool = False
    alarm_low: Optional[float] = None
    alarm_high: Optional[float] = None
    alarm_level: str = "warning"
    scale: float = 1.0
    offset: float = 0.0


class DataPointCreate(BaseModel):
    point_code: str = Field(..., min_length=1, max_length=50)
    point_name: str = Field(..., min_length=1, max_length=200)
    hierarchy_id: int
    device_id: Optional[int] = None
    location_desc: Optional[str] = None
    longitude: Optional[float] = None
    latitude: Optional[float] = None
    items: List[DataItemCreate] = []


class DataPointUpdate(BaseModel):
    point_name: Optional[str] = None
    hierarchy_id: Optional[int] = None
    device_id: Optional[int] = None
    location_desc: Optional[str] = None
    longitude: Optional[float] = None
    latitude: Optional[float] = None
    status: Optional[str] = None


# ============ 协议模板 ============

class ProtocolCreate(BaseModel):
    template_name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    protocol_type: str
    frame_format: dict


class ProtocolUpdate(BaseModel):
    template_name: Optional[str] = None
    description: Optional[str] = None
    protocol_type: Optional[str] = None
    frame_format: Optional[dict] = None


class ProtocolTestRequest(BaseModel):
    protocol_type: str
    frame_format: dict
    test_data: str = Field(..., description="测试报文，十六进制字符串")


# ============ 用户 ============

class UserCreate(BaseModel):
    username: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=8, max_length=100)
    real_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    role: str = "user"
    hierarchy_id: Optional[int] = None


class UserUpdate(BaseModel):
    real_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    hierarchy_id: Optional[int] = None
    status: Optional[str] = None


# ============ 告警 ============

class AlarmAckRequest(BaseModel):
    remark: Optional[str] = None


class AlarmConfigUpdate(BaseModel):
    alarm_enabled: Optional[bool] = None
    alarm_low: Optional[float] = None
    alarm_high: Optional[float] = None
    alarm_level: Optional[str] = None


# ============ 系统配置 ============

class SystemConfigUpdate(BaseModel):
    config_value: str
