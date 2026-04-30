"""告警模型"""
from sqlalchemy import Column, Integer, String, Float, Boolean, Text, TIMESTAMP, ForeignKey, Time
from sqlalchemy.sql import func
from app.database import Base


class AlarmRecord(Base):
    __tablename__ = "alarm_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    point_id = Column(Integer, ForeignKey("data_points.id"), comment="关联数据点")
    item_id = Column(Integer, ForeignKey("data_items.id"), comment="关联数据项")
    alarm_type = Column(String(20), nullable=False, comment="告警类型: high/low/offline/sudden_change/data_zero/data_dup")
    alarm_value = Column(Float, comment="触发告警的值")
    threshold = Column(Float, comment="告警阈值")
    alarm_level = Column(String(20), default="warning", comment="告警级别: warning/critical")
    status = Column(String(20), default="active", comment="状态: active/acked/resolved/suppressed")
    acked_by = Column(Integer, ForeignKey("users.id"), comment="确认人")
    acked_at = Column(TIMESTAMP, comment="确认时间")
    resolved_at = Column(TIMESTAMP, comment="解除时间")
    notify_sent = Column(Boolean, default=False, comment="是否已发送通知")
    notify_result = Column(Text, comment="通知发送结果")
    created_at = Column(TIMESTAMP, server_default=func.now())


class AlarmNotification(Base):
    __tablename__ = "alarm_notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), comment="关联用户")
    hierarchy_id = Column(Integer, ForeignKey("hierarchy_levels.id"), comment="关联层级")
    notify_type = Column(String(20), nullable=False, comment="通知方式: sms/phone/both")
    phone_number = Column(String(20), comment="通知手机号")
    alarm_level_filter = Column(String(20), default="all", comment="接收级别: warning/critical/all")
    quiet_start = Column(Time, comment="免打扰开始时间")
    quiet_end = Column(Time, comment="免打扰结束时间")
    enabled = Column(Boolean, default=True, comment="是否启用")
    created_at = Column(TIMESTAMP, server_default=func.now())
