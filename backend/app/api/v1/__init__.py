"""API路由注册"""
from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.hierarchy import router as hierarchy_router
from app.api.v1.users import router as users_router
from app.api.v1.devices import router as devices_router
from app.api.v1.data_points import router as data_points_router
from app.api.v1.protocols import router as protocols_router
from app.api.v1.realtime import router as realtime_router
from app.api.v1.history import router as history_router
from app.api.v1.alarms import router as alarms_router
from app.api.v1.reports import router as reports_router
from app.api.v1.system import router as system_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth_router)
api_router.include_router(hierarchy_router)
api_router.include_router(users_router)
api_router.include_router(devices_router)
api_router.include_router(data_points_router)
api_router.include_router(protocols_router)
api_router.include_router(realtime_router)
api_router.include_router(history_router)
api_router.include_router(alarms_router)
api_router.include_router(reports_router)
api_router.include_router(system_router)
