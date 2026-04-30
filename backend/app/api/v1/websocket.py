"""WebSocket 实时推送服务

WebSocket端点: /ws/realtime
支持: JWT认证、数据订阅、实时推送、告警通知
"""
import json
import logging
import asyncio
from datetime import datetime, timezone
from typing import Dict, Optional, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from jose import JWTError, jwt

from app.config import settings

logger = logging.getLogger("industrial-monitor.websocket")

router = APIRouter(tags=["WebSocket"])


class ConnectionManager:
    """WebSocket连接管理器"""

    def __init__(self):
        # {user_id: {ws: WebSocket, subscribed_points: set}}
        self._connections: Dict[int, Dict] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        async with self._lock:
            self._connections[user_id] = {
                "ws": websocket,
                "subscribed_points": set(),
                "connected_at": datetime.now(timezone.utc),
            }
        logger.info(f"WebSocket连接: user_id={user_id}")

    async def disconnect(self, user_id: int):
        async with self._lock:
            self._connections.pop(user_id, None)
        logger.info(f"WebSocket断开: user_id={user_id}")

    async def subscribe(self, user_id: int, point_ids: list):
        async with self._lock:
            if user_id in self._connections:
                self._connections[user_id]["subscribed_points"].update(point_ids)

    async def unsubscribe(self, user_id: int, point_ids: list):
        async with self._lock:
            if user_id in self._connections:
                self._connections[user_id]["subscribed_points"].difference_update(point_ids)

    async def send_to_user(self, user_id: int, message: dict):
        """发送消息给指定用户"""
        conn = self._connections.get(user_id)
        if conn:
            try:
                await conn["ws"].send_json(message)
            except Exception:
                await self.disconnect(user_id)

    async def broadcast_data(self, point_id: int, data: dict):
        """向订阅了该数据点的所有用户推送数据"""
        message = {"type": "data_update", "point_id": point_id, "data": data}
        disconnected = []

        # 拷贝一份 keys 避免遍历时修改字典
        for user_id in list(self._connections.keys()):
            conn = self._connections.get(user_id)
            if not conn or point_id not in conn["subscribed_points"]:
                continue
            try:
                await conn["ws"].send_json(message)
            except Exception:
                disconnected.append(user_id)

        for uid in disconnected:
            await self.disconnect(uid)

    async def broadcast_alarm(self, alarm_data: dict):
        """广播告警给所有连接的用户"""
        message = {"type": "alarm", "data": alarm_data}
        disconnected = []

        for user_id in list(self._connections.keys()):
            conn = self._connections.get(user_id)
            if not conn:
                continue
            try:
                await conn["ws"].send_json(message)
            except Exception:
                disconnected.append(user_id)

        for uid in disconnected:
            await self.disconnect(uid)

    @property
    def connection_count(self) -> int:
        return len(self._connections)

    def get_subscribed_users(self, point_id: int) -> list:
        return [
            uid for uid, conn in self._connections.items()
            if point_id in conn["subscribed_points"]
        ]


# 全局连接管理器
manager = ConnectionManager()


def _verify_ws_token(token: str) -> Optional[int]:
    """验证WebSocket JWT Token，返回user_id"""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id = payload.get("sub")
        if user_id and payload.get("type") == "access":
            return int(user_id)
    except JWTError:
        pass
    return None


@router.websocket("/ws/realtime")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
):
    """
    WebSocket实时数据推送端点

    连接: ws://host/ws/realtime?token=<jwt_token>

    消息格式:
    客户端 -> 服务端:
        {"action": "subscribe", "point_ids": [1, 2, 3]}
        {"action": "unsubscribe", "point_ids": [1, 2, 3]}
        {"action": "ping"}

    服务端 -> 客户端:
        {"type": "data_update", "point_id": 1, "data": {...}}
        {"type": "alarm", "data": {...}}
        {"type": "pong"}
    """
    # JWT认证
    if not token:
        await websocket.close(code=4001, reason="Missing token")
        return

    user_id = _verify_ws_token(token)
    if not user_id:
        await websocket.close(code=4001, reason="Invalid token")
        return

    await manager.connect(websocket, user_id)

    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                action = message.get("action")

                if action == "subscribe":
                    point_ids = message.get("point_ids", [])
                    await manager.subscribe(user_id, point_ids)
                    await websocket.send_json({
                        "type": "subscribed",
                        "point_ids": point_ids,
                    })

                elif action == "unsubscribe":
                    point_ids = message.get("point_ids", [])
                    await manager.unsubscribe(user_id, point_ids)
                    await websocket.send_json({
                        "type": "unsubscribed",
                        "point_ids": point_ids,
                    })

                elif action == "ping":
                    await websocket.send_json({"type": "pong"})

                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"未知操作: {action}",
                    })

            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "无效的JSON格式",
                })

    except WebSocketDisconnect:
        await manager.disconnect(user_id)
    except Exception as e:
        logger.error(f"WebSocket异常: {e}", exc_info=True)
        await manager.disconnect(user_id)


def get_ws_manager() -> ConnectionManager:
    """获取WebSocket连接管理器"""
    return manager
