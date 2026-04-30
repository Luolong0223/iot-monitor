"""TCP数据处理器

处理从TCP服务器接收到的DTU设备二进制数据。
"""
import logging
from datetime import datetime, timezone

from app.database import async_session
from app.models.device import Device
from app.models.data_point import DataPoint
from app.models.protocol import ProtocolTemplate
from app.services.protocol_parser import ProtocolParser
from app.services.tdengine_service import get_tdengine_service
from app.services.alarm_engine import get_alarm_engine
from sqlalchemy import select

logger = logging.getLogger("industrial-monitor.tcp_handler")


async def handle_tcp_data(client_key: str, raw_data: bytes, timestamp: datetime):
    """
    处理TCP接收到的二进制数据

    流程:
    1. 根据客户端IP/端口查找设备
    2. 使用关联的协议模板解析数据
    3. 存储到TDengine
    4. 检查告警
    """
    try:
        async with async_session() as db:
            # 根据客户端地址查找设备 (client_key 格式: "IP:PORT")
            # 这里简化为查找所有使用tcp通讯的设备，实际应有更精确的匹配
            ip = client_key.split(":")[0] if ":" in client_key else client_key

            # 查找设备 (可通过SIM卡号或设备编码匹配)
            result = await db.execute(
                select(Device).where(
                    Device.comm_mode == "tcp",
                    Device.status != "maintenance",
                )
            )
            devices = result.scalars().all()

            # 尝试匹配设备 (通过数据中的设备标识)
            device = _match_device(devices, raw_data)
            if not device:
                logger.warning(f"TCP数据无法匹配设备: {client_key}, 数据长度={len(raw_data)}")
                return

            # 更新心跳
            device.last_heartbeat = timestamp
            if device.status == "offline":
                device.status = "online"
                alarm_engine = get_alarm_engine()
                dp_result = await db.execute(
                    select(DataPoint.id).where(DataPoint.device_id == device.id)
                )
                for pid in dp_result.scalars():
                    await alarm_engine.auto_resolve_offline_alarms(db, pid)

            # 协议解析
            if not device.protocol_id:
                logger.warning(f"设备 {device.device_code} 未配置协议模板")
                await db.commit()
                return

            proto_result = await db.execute(
                select(ProtocolTemplate).where(ProtocolTemplate.id == device.protocol_id)
            )
            protocol = proto_result.scalar_one_or_none()
            if not protocol:
                await db.commit()
                return

            parser = ProtocolParser()
            hex_data = raw_data.hex()

            try:
                parsed = parser.parse(
                    protocol_type=protocol.protocol_type,
                    frame_format=protocol.frame_format,
                    hex_data=hex_data,
                )
            except Exception as e:
                logger.error(f"TCP协议解析失败 [{device.device_code}]: {e}")
                await db.commit()
                return

            # 存储数据
            values = parsed.get("values", {})
            if isinstance(values, dict):
                await _store_parsed_data(db, device, values, timestamp)

            await db.commit()

    except Exception as e:
        logger.error(f"TCP数据处理异常 [{client_key}]: {e}", exc_info=True)


def _match_device(devices, raw_data: bytes):
    """
    匹配设备 - 根据数据中的设备标识
    实际项目中应根据协议格式提取设备地址/编码进行匹配
    """
    # 简化实现: 如果只有一个设备则直接匹配
    if len(devices) == 1:
        return devices[0]

    # TODO: 根据协议从数据中提取设备标识进行精确匹配
    # 例如 Modbus RTU 中的 slave_id
    return devices[0] if devices else None


async def _store_parsed_data(db, device: Device, values: dict, timestamp: datetime):
    """存储解析后的数据"""
    tdengine = get_tdengine_service()
    alarm_engine = get_alarm_engine()

    # 查找设备关联的数据点
    dp_result = await db.execute(
        select(DataPoint).where(DataPoint.device_id == device.id)
    )
    points = dp_result.scalars().all()

    for point in points:
        for item in (point.items or []):
            value = values.get(item.item_code)
            if value is None:
                continue

            try:
                numeric_value = float(value)
            except (TypeError, ValueError):
                continue

            # 换算
            converted = numeric_value * item.scale + item.offset

            # 存储
            if tdengine.connected:
                tdengine.insert_data(
                    point_id=point.id,
                    item_id=item.id,
                    item_code=item.item_code,
                    point_code=point.point_code,
                    value=converted,
                    timestamp=timestamp,
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
