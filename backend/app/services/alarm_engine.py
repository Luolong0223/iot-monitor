"""告警引擎

告警检查、创建、抑制、升级、通知和自动解除。
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models.alarm import AlarmRecord
from app.models.data_point import DataItem

logger = logging.getLogger("industrial-monitor.alarm")

# 告警升级时间阈值 (分钟)
ESCALATION_THRESHOLDS = {
    "warning": [15, 30, 60],
    "critical": [10, 20, 40],
}

# 告警抑制时间 (同类型同数据项，分钟)
SUPPRESSION_MINUTES = 5


class AlarmEngine:
    """告警引擎"""

    def __init__(self):
        self._ws_notify_callback = None  # WebSocket通知回调

    def set_ws_notify_callback(self, callback):
        """设置WebSocket通知回调"""
        self._ws_notify_callback = callback

    async def check_and_create_alarm(
        self,
        db: AsyncSession,
        point_id: int,
        item_id: int,
        value: float,
        item_config: dict,
    ) -> Optional[AlarmRecord]:
        """
        检查数据是否触发告警，如果触发则创建告警记录

        Args:
            db: 数据库会话
            point_id: 数据点ID
            item_id: 数据项ID
            value: 当前值
            item_config: 数据项配置 (alarm_enabled, alarm_low, alarm_high, alarm_level)
        """
        if not item_config.get("alarm_enabled", False):
            return None

        alarm_low = item_config.get("alarm_low")
        alarm_high = item_config.get("alarm_high")
        alarm_level = item_config.get("alarm_level", "warning")

        # 判断告警类型
        alarm_type = None
        threshold = None

        if alarm_high is not None and value > alarm_high:
            alarm_type = "high"
            threshold = alarm_high
        elif alarm_low is not None and value < alarm_low:
            alarm_type = "low"
            threshold = alarm_low

        if not alarm_type:
            return None

        # 告警抑制检查
        if await self._is_suppressed(db, item_id, alarm_type):
            logger.debug(f"告警被抑制: item_id={item_id}, type={alarm_type}")
            return None

        # 创建告警记录
        alarm = AlarmRecord(
            point_id=point_id,
            item_id=item_id,
            alarm_type=alarm_type,
            alarm_value=value,
            threshold=threshold,
            alarm_level=alarm_level,
            status="active",
        )
        db.add(alarm)
        await db.flush()
        await db.refresh(alarm)

        logger.warning(
            f"告警创建: ID={alarm.id}, 数据点={point_id}, 数据项={item_id}, "
            f"类型={alarm_type}, 值={value}, 阈值={threshold}"
        )

        # 发送WebSocket通知
        await self._send_ws_notification(alarm)

        return alarm

    async def check_data_quality_alarm(
        self,
        db: AsyncSession,
        point_id: int,
        item_id: int,
        alarm_type: str,
        value: float,
        detail: str = "",
    ) -> Optional[AlarmRecord]:
        """
        数据质量告警 (突变、零值、重复等)

        Args:
            alarm_type: sudden_change / data_zero / data_dup
        """
        # 告警抑制
        if await self._is_suppressed(db, item_id, alarm_type):
            return None

        alarm = AlarmRecord(
            point_id=point_id,
            item_id=item_id,
            alarm_type=alarm_type,
            alarm_value=value,
            threshold=None,
            alarm_level="warning",
            status="active",
        )
        db.add(alarm)
        await db.flush()
        await db.refresh(alarm)

        logger.warning(f"数据质量告警: ID={alarm.id}, 类型={alarm_type}, 值={value}")

        await self._send_ws_notification(alarm)
        return alarm

    async def create_offline_alarm(
        self,
        db: AsyncSession,
        point_id: int,
        device_id: int,
    ) -> Optional[AlarmRecord]:
        """设备离线告警"""
        # 检查是否已有活跃的离线告警
        existing = await db.execute(
            select(AlarmRecord).where(
                and_(
                    AlarmRecord.point_id == point_id,
                    AlarmRecord.alarm_type == "offline",
                    AlarmRecord.status == "active",
                )
            )
        )
        if existing.scalar_one_or_none():
            return None

        alarm = AlarmRecord(
            point_id=point_id,
            item_id=None,
            alarm_type="offline",
            alarm_value=None,
            threshold=None,
            alarm_level="critical",
            status="active",
        )
        db.add(alarm)
        await db.flush()
        await db.refresh(alarm)

        logger.warning(f"设备离线告警: ID={alarm.id}, 数据点={point_id}")
        await self._send_ws_notification(alarm)
        return alarm

    async def auto_resolve_offline_alarms(
        self,
        db: AsyncSession,
        point_id: int,
    ):
        """设备上线时自动解除离线告警"""
        result = await db.execute(
            select(AlarmRecord).where(
                and_(
                    AlarmRecord.point_id == point_id,
                    AlarmRecord.alarm_type == "offline",
                    AlarmRecord.status == "active",
                )
            )
        )
        alarms = result.scalars().all()

        for alarm in alarms:
            alarm.status = "resolved"
            alarm.resolved_at = datetime.now(timezone.utc)
            logger.info(f"自动解除离线告警: ID={alarm.id}")

        if alarms:
            await db.commit()

    async def check_escalation(self, db: AsyncSession):
        """检查告警升级（定期调用）"""
        now = datetime.now(timezone.utc)

        # 查找所有活跃告警
        result = await db.execute(
            select(AlarmRecord).where(AlarmRecord.status == "active")
        )
        active_alarms = result.scalars().all()

        escalated = 0
        for alarm in active_alarms:
            if not alarm.created_at:
                continue

            # 确保 created_at 有时区信息
            created_at = alarm.created_at
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)

            duration_minutes = (now - created_at).total_seconds() / 60
            current_level = alarm.alarm_level or "warning"
            thresholds = ESCALATION_THRESHOLDS.get(current_level, [15, 30, 60])

            # 确定应该升级到的级别
            new_level = None
            if duration_minutes >= thresholds[-1] and current_level != "critical":
                new_level = "critical"
            elif len(thresholds) > 1 and duration_minutes >= thresholds[-2] and current_level == "warning":
                new_level = "warning"  # 保持但可扩展

            if new_level and new_level != current_level:
                alarm.alarm_level = new_level
                escalated += 1
                logger.warning(f"告警升级: ID={alarm.id}, {current_level} -> {new_level}")

        if escalated > 0:
            await db.commit()
            logger.info(f"告警升级检查完成: {escalated} 条升级")

    async def _is_suppressed(
        self,
        db: AsyncSession,
        item_id: int,
        alarm_type: str,
    ) -> bool:
        """检查告警是否应被抑制"""
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=SUPPRESSION_MINUTES)

        result = await db.execute(
            select(AlarmRecord).where(
                and_(
                    AlarmRecord.item_id == item_id,
                    AlarmRecord.alarm_type == alarm_type,
                    AlarmRecord.status.in_(["active", "acked"]),
                    AlarmRecord.created_at >= cutoff,
                )
            )
        )
        return result.scalar_one_or_none() is not None

    async def _send_ws_notification(self, alarm: AlarmRecord):
        """发送WebSocket通知"""
        if not self._ws_notify_callback:
            return

        try:
            notification = {
                "type": "alarm",
                "data": {
                    "id": alarm.id,
                    "point_id": alarm.point_id,
                    "item_id": alarm.item_id,
                    "alarm_type": alarm.alarm_type,
                    "alarm_value": alarm.alarm_value,
                    "threshold": alarm.threshold,
                    "alarm_level": alarm.alarm_level,
                    "status": alarm.status,
                    "created_at": alarm.created_at.isoformat() if alarm.created_at else None,
                },
            }
            await self._ws_notify_callback(notification)
        except Exception as e:
            logger.error(f"WebSocket通知发送失败: {e}")


# 全局单例
_alarm_engine: Optional[AlarmEngine] = None


def get_alarm_engine() -> AlarmEngine:
    """获取告警引擎实例"""
    global _alarm_engine
    if _alarm_engine is None:
        _alarm_engine = AlarmEngine()
    return _alarm_engine
