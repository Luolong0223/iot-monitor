"""FastAPI 应用入口"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import time

from app.config import settings
from app.database import init_db, close_db
from app.api.v1 import api_router
from app.api.v1.websocket import router as ws_router


# 日志配置
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("industrial-monitor")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info(f"🚀 {settings.SYSTEM_NAME} 启动中...")

    # 初始化数据库
    await init_db()
    logger.info("✅ 数据库初始化完成")

    # 启动 TDengine 连接
    from app.services.tdengine_service import get_tdengine_service
    tdengine = get_tdengine_service()
    tdengine.connect()
    logger.info("✅ TDengine 连接完成")

    # 启动 MQTT 客户端
    import asyncio
    from app.mqtt.client import get_mqtt_client
    from app.services.mqtt_handler import handle_mqtt_message

    mqtt_client = get_mqtt_client()
    mqtt_client.set_on_message_callback(handle_mqtt_message)
    mqtt_client.start(asyncio.get_event_loop())
    logger.info("✅ MQTT客户端已启动")

    # 启动 TCP 服务器
    from app.tcp.server import get_tcp_server
    from app.services.tcp_handler import handle_tcp_data

    tcp_server = get_tcp_server()
    tcp_server.set_on_data_callback(handle_tcp_data)
    await tcp_server.start()
    logger.info("✅ TCP服务器已启动")

    # 启动定时任务调度器
    from app.services.scheduler import start_scheduler
    start_scheduler()
    logger.info("✅ 定时任务调度器已启动")

    logger.info(f"🎉 {settings.SYSTEM_NAME} 启动完成")

    yield

    # 关闭
    logger.info("🛑 应用关闭中...")

    from app.services.scheduler import stop_scheduler
    stop_scheduler()

    tcp_server = get_tcp_server()
    await tcp_server.stop()

    mqtt_client = get_mqtt_client()
    mqtt_client.stop()

    tdengine.close()
    await close_db()

    logger.info("✅ 应用已关闭")


# 创建应用
app = FastAPI(
    title=settings.SYSTEM_NAME,
    version="1.0.0",
    description="工业数据采集管理平台 API",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 请求耗时中间件
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = f"{process_time:.4f}"
    return response


# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"未处理的异常: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"code": 500, "message": "服务器内部错误", "data": None},
    )


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={"code": 404, "message": "接口不存在", "data": None},
    )


# 注册路由
app.include_router(api_router)
app.include_router(ws_router)


# 健康检查
@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/")
async def root():
    return {"message": settings.SYSTEM_NAME, "docs": "/api/docs"}
