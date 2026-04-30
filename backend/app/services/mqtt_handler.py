"""MQTT消息处理器

处理从MQTT接收到的设备数据、心跳和状态消息。
"""
import json
import logging
from datetime import datetime, timezone
from typing import Optional

from app.database import async_session
from app.models.device import Device
from app.models.data_point import DataPoint, DataItem
from app.services.protocol_parser import ProtocolParser
from app.services.data_validator import get_validator
from app.services.tdengine_service import get_tdengine_service
from app.services.alarm_engine import get_alarm_engine
from app.api.v1.websocket import get_ws_manager
from sqlalchemy import select

logger = logging.getLogger("industrial-monitor.mqtt_handler")


async def handle_mqtt_message(topic: str, payload: dict):
    """
    处理MQTT消息

    主题格式:
    - iot/device/{device_code}/data     → 设备数据上报
    - iot/device/{device_code}/heartbeat → 心跳
    - iot/device/{device_code}/status    → 状态变更
    """
    try:
        parts = topic.split("/")
        if len(parts) < 4:
            return

        device_code = parts[2]
        msg_type = parts[3]

        if msg_type == "data":
            await _handle_device_data(device_code, payload)
        elif msg_type == "heartbeat":
            await _handle_heartbeat(device_code, payload)
        elif msg_type == "status":
            await _handle_device_status(device_code, payload)
    except Exception as e:
        logger.error(f"MQTT消息处理失败 [{topic}]: {e}", exc_info=True)


async def _handle_device_data(device_code: str, payload: dict):
    """处理设备数据上报"""
    async with async_session() as db:
        # 查找设备
        result = await db.execute(
            select(Device).where(Device.device_code == device_code)
        )
        device = result.scalar_one_or_none()
        if not device:
            logger.warning(f"未知设备: {device_code}")
            return

        # 更新心跳
        device.last_heartbeat = datetime.now(timezone.utc)
        if device.status == "offline":
            device.status = "online"
            # 自动解除离线告警
            alarm_engine = get_alarm_engine()
            dp_result = await db.execute(
                select(DataPoint.id).where(DataPoint.device_id == device.id)
            )
            for pid in dp_result.scalars():
                await alarm_engine.auto_resolve_offline_alarms(db, pid)

        # 如果设备有协议配置，使用协议解析器
        raw_hex = payload.get("raw_data")
        if raw_hex and device.protocol_id:
            from app.models.protocol import ProtocolTemplate
            proto_result = await db.execute(
                select(ProtocolTemplate).where(ProtocolTemplate.id == device.protocol_id)
            )
            protocol = proto_result.scalar_one_or_none()
            if protocol:
                parser = ProtocolParser()
                try:
                    parsed = parser.parse(
                        protocol_type=protocol.protocol_type,
                        frame_format=protocol.frame_format,
                        hex_data=raw_hex,
                    )
                    payload = {**payload, **parsed.get("values", {})}
                except Exception as e:
                    logger.error(f"协议解析失败 [{device_code}]: {e}")

        # 处理数据项
        await _process_data_items(db, device, payload)
        await db.commit()


async def _process_data_items(db, device: Device, payload: dict):
    """处理数据项"""
    tdengine = get_tdengine_service()
    validator = get_validator()
    alarm_engine = get_alarm_engine()
    ws_manager = get_ws_manager()

    # 查找设备关联的所有数据点
    dp_result = await db.execute(
        select(DataPoint).where(DataPoint.device_id == device.id)
    )
    points = dp_result.scalars().all()

    for point in points:
        for item in (point.items or []):
            # 从payload中提取值
            value = payload.get(item.item_code)
            if value is None:
                continue

            try:
                numeric_value = float(value)
            except (TypeError, ValueError):
                continue

            # 应用换算
            converted = numeric_value * item.scale + item.offset

            # 数据校验
            validation_config = {
                "validation_enabled": item.validation_enabled,
                "min_value": item.min_value,
                "max_value": item.max_value,
                "jump_threshold": item.jump_threshold,
                "jump_window_size": item.jump_window_size,
                "zero_count_limit": item.zero_count_limit,
                "dup_count_limit": item.dup_count_limit,
            }
            vr = validator.validate(item.id, converted, validation_config)

            # 存储到 TDengine
            if tdengine.connected:
                tdengine.insert_data(
                    point_id=point.id,
                    item_id=item.id,
                    item_code=item.item_code,
                    point_code=point.point_code,
                    value=converted,
                    quality=0 if vr.is_valid else 1,
                    raw_value=numeric_value,
                )

            # 告警检查
            alarm_config = {
                "alarm_enabled": item.alarm_enabled,
                "alarm_low": item.alarm_low,
                "alarm_high": item.alarm_high,
                "alarm_level": item.alarm_level,
            }
            await alarm_engine.check_and_create_alarm(
                db, point.id, item.id, converted, alarm_config
            )

            # 数据质量告警
            if vr.warnings:
                for warning in vr.warnings:
                    if "突变" in warning:
                        await alarm_engine.check_data_quality_alarm(
                            db, point.id, item.id, "sudden_change", converted
                        )
                    elif "连续" in warning and "零" in warning:
                        await alarm_engine.check_data_quality_alarm(
                            db, point.id, item.id, "data_zero", converted
                        )
                    elif "连续" in warning and "相同" in warning:
                        await alarm_engine.check_data_quality_alarm(
                            db, point.id, item.id, "data_dup", converted
                        )

            # WebSocket 推送
            ws_data = {
                "item_id": item.id,
                "item_code": item.item_code,
                "value": round(converted, 4),
                "unit": item.unit,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "quality": 0 if vr.is_valid else 1,
            }
            await ws_manager.broadcast_data(point.id, ws_data)


async def _handle_heartbeat(device_code: str, payload: dict):
    """处理设备心跳"""
    async with async_session() as db:
        result = await db.execute(
            select(Device).where(Device.device_code == device_code)
        )
        device = result.scalar_one_or_none()
        if not device:
            return

        device.last_heartbeat = datetime.now(timezone.utc)

        # 设备从离线恢复
        if device.status == "offline":
            device.status = "online"
            alarm_engine = get_alarm_engine()
            dp_result = await db.execute(
                select(DataPoint.id).where(DataPoint.device_id == device.id)
            )
            for pid in dp_result.scalars():
                await alarm_engine.auto_resolve_offline_alarms(db, pid)

        # 更新固件版本
        firmware = payload.get("firmware_version")
        if firmware:
            device.firmware_version = firmware

        await db.commit()


async def _handle_device_status(device_code: str, payload: dict):
    """处理设备状态变更"""
    async with async_session() as db:
        result = await db.execute(
            select(Device).where(Device.device_code == device_code)
        )
        device = result.scalar_one_or_none()
        if not device:
            return

        new_status = payload.get("status")
        if new_status in ("online", "offline", "maintenance"):
            device.status = new_status

        device.last_heartbeat = datetime.now(timezone.utc)
        await db.commit()
