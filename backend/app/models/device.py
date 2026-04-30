"""设备模型"""
from sqlalchemy import Column, Integer, String, Text, Date, TIMESTAMP, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_code = Column(String(100), unique=True, nullable=False, comment="设备编码/IMEI")
    device_name = Column(String(200), comment="设备名称")
    device_type = Column(String(50), default="4g_dtu", comment="设备类型: 4g_dtu/gateway/other")
    hierarchy_id = Column(Integer, ForeignKey("hierarchy_levels.id"), comment="所属层级节点")
    comm_mode = Column(String(20), default="mqtt", comment="通讯方式: mqtt/tcp/udp")
    protocol_id = Column(Integer, ForeignKey("protocol_templates.id"), comment="关联协议模板")
    sim_card = Column(String(20), comment="SIM卡号")
    install_date = Column(Date, comment="安装日期")
    status = Column(String(20), default="online", comment="状态: online/offline/maintenance")
    last_heartbeat = Column(TIMESTAMP, comment="最后心跳时间")
    firmware_version = Column(String(50), comment="固件版本号")
    remark = Column(Text, comment="备注")
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    # 关系
    hierarchy = relationship("HierarchyLevel", back_populates="devices")
    protocol = relationship("ProtocolTemplate", back_populates="devices")
    data_points = relationship("DataPoint", back_populates="device", lazy="selectin")
