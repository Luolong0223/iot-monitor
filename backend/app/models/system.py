"""系统配置和操作日志模型"""
from sqlalchemy import Column, Integer, String, Text, Boolean, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.database import Base


class SystemConfig(Base):
    __tablename__ = "system_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    config_key = Column(String(100), unique=True, nullable=False, comment="配置项键名")
    config_value = Column(Text, comment="配置项值")
    config_group = Column(String(50), comment="配置分组")
    value_type = Column(String(20), default="string", comment="值类型: string/number/boolean/json")
    description = Column(Text, comment="配置说明")
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())


class OperationLog(Base):
    __tablename__ = "operation_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), comment="操作用户")
    username = Column(String(50), comment="用户名")
    action = Column(String(50), comment="操作类型: login/logout/create/update/delete/export")
    module = Column(String(50), comment="操作模块")
    target_id = Column(Integer, comment="操作对象ID")
    target_desc = Column(String(200), comment="操作对象描述")
    detail = Column(JSONB, comment="操作详情")
    ip_address = Column(String(50), comment="操作IP")
    user_agent = Column(String(500), comment="浏览器标识")
    created_at = Column(TIMESTAMP, server_default=func.now())
