"""请求频率限制中间件"""
import time
import logging
from collections import defaultdict
from typing import Dict, Tuple

from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("industrial-monitor.ratelimit")

# 存储: {ip: (请求次数, 窗口开始时间)}
_request_counts: Dict[str, Tuple[int, float]] = {}

# 配置
RATE_LIMIT = 100      # 每窗口最大请求数
RATE_WINDOW = 60      # 窗口大小(秒)
WS_RATE_LIMIT = 20    # WebSocket 消息频率限制


def get_client_ip(request: Request) -> str:
    """获取客户端真实IP"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def rate_limit_middleware(request: Request, call_next):
    """请求频率限制"""
    # 健康检查和文档不限制
    if request.url.path in ("/health", "/", "/api/docs", "/api/redoc", "/openapi.json"):
        return await call_next(request)

    client_ip = get_client_ip(request)
    now = time.time()

    count, window_start = _request_counts.get(client_ip, (0, now))

    # 窗口过期，重置
    if now - window_start > RATE_WINDOW:
        count = 0
        window_start = now

    count += 1
    _request_counts[client_ip] = (count, window_start)

    if count > RATE_LIMIT:
        logger.warning(f"频率限制触发: {client_ip} ({count}/{RATE_WINDOW}s)")
        return JSONResponse(
            status_code=429,
            content={"code": 429, "message": "请求过于频繁，请稍后再试", "data": None},
        )

    return await call_next(request)
