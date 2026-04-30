"""层级结构模型"""
from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class HierarchyLevel(Base):
    __tablename__ = "hierarchy_levels"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment="层级名称")
    parent_id = Column(Integer, ForeignKey("hierarchy_levels.id"), nullable=True, comment="父级ID")
    level_type = Column(String(50), nullable=False, comment="层级类型: province/city/district/site")
    sort_order = Column(Integer, default=0, comment="排序序号")
    description = Column(Text, comment="描述信息")
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    # 关系
    children = relationship("HierarchyLevel", back_populates="parent", lazy="selectin")
    parent = relationship("HierarchyLevel", back_populates="children", remote_side=[id])
    devices = relationship("Device", back_populates="hierarchy", lazy="selectin")
    data_points = relationship("DataPoint", back_populates="hierarchy", lazy="selectin")
    users = relationship("User", back_populates="hierarchy", lazy="selectin")
