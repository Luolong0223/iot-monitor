"""数据点和数据项模型"""
from sqlalchemy import Column, Integer, String, Float, Boolean, Text, TIMESTAMP, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class DataPoint(Base):
    __tablename__ = "data_points"

    id = Column(Integer, primary_key=True, autoincrement=True)
    point_code = Column(String(50), unique=True, nullable=False, comment="数据点编码")
    point_name = Column(String(200), nullable=False, comment="数据点名称")
    hierarchy_id = Column(Integer, ForeignKey("hierarchy_levels.id"), comment="所属层级节点")
    device_id = Column(Integer, ForeignKey("devices.id"), comment="关联设备")
    location_desc = Column(Text, comment="位置描述")
    longitude = Column(Float, comment="经度")
    latitude = Column(Float, comment="纬度")
    status = Column(String(20), default="active", comment="状态: active/inactive/maintenance")
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    # 关系
    hierarchy = relationship("HierarchyLevel", back_populates="data_points")
    device = relationship("Device", back_populates="data_points")
    items = relationship("DataItem", back_populates="point", cascade="all, delete-orphan", lazy="selectin")


class DataItem(Base):
    __tablename__ = "data_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    point_id = Column(Integer, ForeignKey("data_points.id", ondelete="CASCADE"), nullable=False)
    item_code = Column(String(50), nullable=False, comment="数据项编码")
    item_name = Column(String(100), nullable=False, comment="数据项名称")
    unit = Column(String(20), comment="单位")
    data_type = Column(String(20), default="float", comment="数据类型: float/int/bool")
    min_value = Column(Float, comment="量程下限")
    max_value = Column(Float, comment="量程上限")
    alarm_enabled = Column(Boolean, default=False, comment="是否启用告警")
    alarm_low = Column(Float, comment="告警下限值")
    alarm_high = Column(Float, comment="告警上限值")
    alarm_level = Column(String(20), default="warning", comment="告警级别: warning/critical")
    validation_enabled = Column(Boolean, default=True, comment="是否启用数据校验")
    jump_threshold = Column(Float, comment="突变阈值")
    jump_window_size = Column(Integer, default=10, comment="突变检测窗口大小")
    zero_count_limit = Column(Integer, default=5, comment="连续零值告警阈值")
    dup_count_limit = Column(Integer, default=10, comment="连续重复值告警阈值")
    scale = Column(Float, default=1.0, comment="换算系数")
    offset = Column(Float, default=0.0, comment="换算偏移")
    sort_order = Column(Integer, default=0, comment="排序")
    created_at = Column(TIMESTAMP, server_default=func.now())

    # 关系
    point = relationship("DataPoint", back_populates="items")
