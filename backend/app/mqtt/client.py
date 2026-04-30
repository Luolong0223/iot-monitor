"""MQTT客户端服务

连接EMQX Broker，订阅设备数据主题，解析存储数据。
"""
import json
import logging
import asyncio
import ssl
from datetime import datetime, timezone
from typing import Optional, Callable

import paho.mqtt.client as mqtt

from app.config import settings

logger = logging.getLogger("industrial-monitor.mqtt")


class MQTTClient:
    """MQTT客户端"""

    def __init__(self):
        self._client: Optional[mqtt.Client] = None
        self._connected = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._on_message_callback: Optional[Callable] = None
        self._reconnect_delay = 1
        self._max_reconnect_delay = 60

    @property
    def connected(self) -> bool:
        return self._connected

    def set_on_message_callback(self, callback: Callable):
        """设置消息回调（异步）"""
        self._on_message_callback = callback

    def start(self, loop: Optional[asyncio.AbstractEventLoop] = None):
        """启动MQTT客户端"""
        self._loop = loop or asyncio.get_event_loop()

        self._client = mqtt.Client(
            client_id="iot-monitor-server",
            protocol=mqtt.MQTTv311,
        )

        # 认证
        if settings.MQTT_USERNAME:
            self._client.username_pw_set(settings.MQTT_USERNAME, settings.MQTT_PASSWORD)

        # 遗嘱消息
        self._client.will_set(
            "iot/server/status",
            payload=json.dumps({"status": "offline", "timestamp": datetime.now(timezone.utc).isoformat()}),
            qos=1,
            retain=True,
        )

        # 回调
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message
        self._client.on_log = self._on_log

        # 自动重连
        self._client.reconnect_delay_set(
            min_delay=self._reconnect_delay,
            max_delay=self._max_reconnect_delay,
        )

        try:
            self._client.connect_async(
                settings.MQTT_BROKER_HOST,
                settings.MQTT_BROKER_PORT,
                keepalive=60,
            )
            self._client.loop_start()
            logger.info(f"MQTT客户端启动，连接 {settings.MQTT_BROKER_HOST}:{settings.MQTT_BROKER_PORT}")
        except Exception as e:
            logger.error(f"MQTT客户端启动失败: {e}")

    def stop(self):
        """停止MQTT客户端"""
        if self._client:
            try:
                self._client.publish(
                    "iot/server/status",
                    payload=json.dumps({"status": "offline", "timestamp": datetime.now(timezone.utc).isoformat()}),
                    qos=1,
                    retain=True,
                )
                self._client.loop_stop()
                self._client.disconnect()
            except Exception as e:
                logger.error(f"MQTT客户端停止异常: {e}")
            self._connected = False
            logger.info("MQTT客户端已停止")

    def publish(self, topic: str, payload: dict, qos: int = 0, retain: bool = False):
        """发布消息"""
        if self._client and self._connected:
            self._client.publish(
                topic,
                payload=json.dumps(payload, ensure_ascii=False),
                qos=qos,
                retain=retain,
            )

    def subscribe(self, topic: str, qos: int = 0):
        """订阅主题"""
        if self._client and self._connected:
            self._client.subscribe(topic, qos=qos)
            logger.info(f"订阅主题: {topic}")

    # ============ 内部回调 ============

    def _on_connect(self, client, userdata, flags, rc):
        """连接成功回调"""
        if rc == 0:
            self._connected = True
            logger.info("MQTT Broker 连接成功")

            # 发布上线状态
            client.publish(
                "iot/server/status",
                payload=json.dumps({"status": "online", "timestamp": datetime.now(timezone.utc).isoformat()}),
                qos=1,
                retain=True,
            )

            # 订阅设备数据主题
            topics = [
                ("iot/device/+/data", 0),       # 设备数据上报
                ("iot/device/+/heartbeat", 0),   # 设备心跳
                ("iot/device/+/status", 1),      # 设备状态
                ("iot/device/+/alarm", 1),       # 设备告警
            ]
            for topic, qos in topics:
                client.subscribe(topic, qos=qos)
                logger.info(f"订阅主题: {topic}")
        else:
            logger.error(f"MQTT连接失败, 返回码: {rc}")

    def _on_disconnect(self, client, userdata, rc):
        """断开连接回调"""
        self._connected = False
        if rc != 0:
            logger.warning(f"MQTT意外断开连接 (rc={rc}), 将自动重连")
        else:
            logger.info("MQTT已断开连接")

    def _on_message(self, client, userdata, msg):
        """消息到达回调"""
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode("utf-8"))

            if self._loop and self._on_message_callback:
                asyncio.run_coroutine_threadsafe(
                    self._on_message_callback(topic, payload),
                    self._loop,
                )
        except json.JSONDecodeError:
            logger.warning(f"MQTT消息JSON解析失败: {msg.topic}")
        except Exception as e:
            logger.error(f"MQTT消息处理异常: {e}", exc_info=True)

    def _on_log(self, client, userdata, level, buf):
        """日志回调"""
        if level == mqtt.MQTT_LOG_ERR:
            logger.error(f"MQTT: {buf}")
        elif level == mqtt.MQTT_LOG_WARNING:
            logger.warning(f"MQTT: {buf}")


# 全局单例
_mqtt_client: Optional[MQTTClient] = None


def get_mqtt_client() -> MQTTClient:
    """获取MQTT客户端实例"""
    global _mqtt_client
    if _mqtt_client is None:
        _mqtt_client = MQTTClient()
    return _mqtt_client
