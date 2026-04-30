"""TCP Server 服务

异步TCP服务器，接受DTU设备连接，解析二进制数据。
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, Callable, Dict

from app.config import settings

logger = logging.getLogger("industrial-monitor.tcp")


class TCPServer:
    """异步TCP服务器"""

    def __init__(self):
        self._server: Optional[asyncio.AbstractServer] = None
        self._clients: Dict[str, asyncio.StreamWriter] = {}
        self._running = False
        self._on_data_callback: Optional[Callable] = None
        self._buffer_size = 4096

    @property
    def running(self) -> bool:
        return self._running

    @property
    def client_count(self) -> int:
        return len(self._clients)

    def set_on_data_callback(self, callback: Callable):
        """设置数据回调"""
        self._on_data_callback = callback

    async def start(self):
        """启动TCP服务器"""
        try:
            self._server = await asyncio.start_server(
                self._handle_client,
                settings.TCP_HOST,
                settings.TCP_PORT,
            )
            self._running = True
            logger.info(f"TCP服务器启动，监听 {settings.TCP_HOST}:{settings.TCP_PORT}")
        except Exception as e:
            logger.error(f"TCP服务器启动失败: {e}")
            raise

    async def stop(self):
        """停止TCP服务器"""
        self._running = False
        if self._server:
            self._server.close()
            await self._server.wait_closed()

        # 关闭所有客户端连接
        for addr, writer in self._clients.items():
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
        self._clients.clear()
        logger.info("TCP服务器已停止")

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """处理客户端连接"""
        addr = writer.get_extra_info("peername")
        client_key = f"{addr[0]}:{addr[1]}"
        self._clients[client_key] = writer
        logger.info(f"DTU设备连接: {client_key}")

        try:
            while self._running:
                data = await asyncio.wait_for(
                    reader.read(self._buffer_size),
                    timeout=300,  # 5分钟超时
                )
                if not data:
                    break

                logger.debug(f"收到 {client_key} 数据: {len(data)} 字节, hex={data.hex()}")

                # 调用数据回调
                if self._on_data_callback:
                    try:
                        await self._on_data_callback(
                            client_key=client_key,
                            raw_data=data,
                            timestamp=datetime.now(timezone.utc),
                        )
                    except Exception as e:
                        logger.error(f"数据处理回调异常: {e}", exc_info=True)

        except asyncio.TimeoutError:
            logger.warning(f"DTU连接超时: {client_key}")
        except ConnectionResetError:
            logger.warning(f"DTU连接重置: {client_key}")
        except Exception as e:
            logger.error(f"DTU连接异常 {client_key}: {e}")
        finally:
            self._clients.pop(client_key, None)
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
            logger.info(f"DTU设备断开: {client_key}")

    async def send_to_client(self, client_key: str, data: bytes) -> bool:
        """向指定客户端发送数据"""
        writer = self._clients.get(client_key)
        if not writer:
            return False
        try:
            writer.write(data)
            await writer.drain()
            return True
        except Exception as e:
            logger.error(f"发送数据失败 {client_key}: {e}")
            return False

    async def broadcast(self, data: bytes):
        """广播数据到所有客户端"""
        for client_key in list(self._clients.keys()):
            await self.send_to_client(client_key, data)


# 全局单例
_tcp_server: Optional[TCPServer] = None


def get_tcp_server() -> TCPServer:
    """获取TCP服务器实例"""
    global _tcp_server
    if _tcp_server is None:
        _tcp_server = TCPServer()
    return _tcp_server
