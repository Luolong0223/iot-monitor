"""协议模板模型"""
from sqlalchemy import Column, Integer, String, Text, Boolean, TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class ProtocolTemplate(Base):
    __tablename__ = "protocol_templates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    template_name = Column(String(200), nullable=False, comment="协议模板名称")
    description = Column(Text, comment="描述")
    protocol_type = Column(String(50), nullable=False, comment="协议类型")
    frame_format = Column(JSONB, nullable=False, comment="帧格式配置JSON")
    is_builtin = Column(Boolean, default=False, comment="是否内置模板")
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    # 关系
    devices = relationship("Device", back_populates="protocol")
