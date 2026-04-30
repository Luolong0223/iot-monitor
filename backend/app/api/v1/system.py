"""系统管理API"""
import logging
import platform
import os
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models.system import SystemConfig, OperationLog
from app.models.device import Device
from app.models.data_point import DataPoint, DataItem
from app.models.alarm import AlarmRecord
from app.models.user import User
from app.schemas import SystemConfigUpdate, ResponseModel
from app.core.security import get_current_user, require_admin, require_superadmin
from app.config import settings

logger = logging.getLogger("industrial-monitor")

router = APIRouter(prefix="/system", tags=["系统管理"])


# ============ 系统配置 ============

@router.get("/config", response_model=ResponseModel)
async def list_configs(
    group: Optional[str] = None,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """系统配置列表"""
    query = select(SystemConfig)
    if group:
        query = query.where(SystemConfig.config_group == group)
    query = query.order_by(SystemConfig.config_group, SystemConfig.id)
    result = await db.execute(query)
    configs = result.scalars().all()

    return ResponseModel(data=[
        {
            "id": c.id,
            "config_key": c.config_key,
            "config_value": c.config_value,
            "config_group": c.config_group,
            "value_type": c.value_type,
            "description": c.description,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        }
        for c in configs
    ])


@router.get("/config/{config_key}", response_model=ResponseModel)
async def get_config(
    config_key: str,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """获取单个配置项"""
    result = await db.execute(
        select(SystemConfig).where(SystemConfig.config_key == config_key)
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="配置项不存在")

    return ResponseModel(data={
        "id": config.id,
        "config_key": config.config_key,
        "config_value": config.config_value,
        "config_group": config.config_group,
        "value_type": config.value_type,
        "description": config.description,
    })


@router.put("/config/{config_key}", response_model=ResponseModel)
async def update_config(
    config_key: str,
    req: SystemConfigUpdate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """修改配置项"""
    result = await db.execute(
        select(SystemConfig).where(SystemConfig.config_key == config_key)
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="配置项不存在")

    config.config_value = req.config_value
    config.updated_at = datetime.now(timezone.utc)
    await db.commit()

    logger.info(f"配置更新: {config_key} = {req.config_value}")
    return ResponseModel(message="配置已更新")


# ============ 健康检查 ============

@router.get("/health", response_model=ResponseModel)
async def health_check(
    db: AsyncSession = Depends(get_db),
):
    """系统健康检查"""
    from app.services.tdengine_service import get_tdengine_service
    from app.mqtt.client import get_mqtt_client
    from app.tcp.server import get_tcp_server

    tdengine = get_tdengine_service()
    mqtt = get_mqtt_client()
    tcp = get_tcp_server()

    # 数据库检查
    db_ok = False
    try:
        await db.execute(select(func.count(User.id)))
        db_ok = True
    except Exception:
        pass

    return ResponseModel(data={
        "status": "ok" if db_ok else "degraded",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "components": {
            "database": "ok" if db_ok else "error",
            "tdengine": "ok" if tdengine.connected else "disconnected",
            "mqtt": "ok" if mqtt.connected else "disconnected",
            "tcp_server": "ok" if tcp.running else "stopped",
        },
        "system": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "cpu_count": os.cpu_count(),
        },
    })


# ============ 操作日志 ============

@router.get("/logs", response_model=ResponseModel)
async def list_operation_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: Optional[int] = None,
    module: Optional[str] = None,
    action: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """操作日志查询"""
    query = select(OperationLog)
    count_query = select(func.count(OperationLog.id))

    if user_id is not None:
        query = query.where(OperationLog.user_id == user_id)
        count_query = count_query.where(OperationLog.user_id == user_id)
    if module:
        query = query.where(OperationLog.module == module)
        count_query = count_query.where(OperationLog.module == module)
    if action:
        query = query.where(OperationLog.action == action)
        count_query = count_query.where(OperationLog.action == action)
    if start_time:
        query = query.where(OperationLog.created_at >= _parse_dt(start_time))
        count_query = count_query.where(OperationLog.created_at >= _parse_dt(start_time))
    if end_time:
        query = query.where(OperationLog.created_at <= _parse_dt(end_time))
        count_query = count_query.where(OperationLog.created_at <= _parse_dt(end_time))

    total = (await db.execute(count_query)).scalar()
    query = query.order_by(OperationLog.id.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    logs = result.scalars().all()

    return ResponseModel(data={
        "list": [
            {
                "id": l.id,
                "user_id": l.user_id,
                "username": l.username,
                "action": l.action,
                "module": l.module,
                "target_id": l.target_id,
                "target_desc": l.target_desc,
                "detail": l.detail,
                "ip_address": l.ip_address,
                "created_at": l.created_at.isoformat() if l.created_at else None,
            }
            for l in logs
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    })


# ============ 手动备份 ============

@router.post("/backup", response_model=ResponseModel)
async def manual_backup(
    current_user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db),
):
    """手动触发备份"""
    import subprocess
    import shutil
    from pathlib import Path

    backup_dir = Path(settings.BACKUP_PATH)
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_dir / f"backup_{timestamp}.sql"

    try:
        # 使用 pg_dump 备份 PostgreSQL
        result = subprocess.run(
            [
                "pg_dump",
                "-h", settings.POSTGRES_HOST,
                "-p", str(settings.POSTGRES_PORT),
                "-U", settings.POSTGRES_USER,
                "-d", settings.POSTGRES_DB,
                "-f", str(backup_file),
            ],
            capture_output=True,
            text=True,
            timeout=300,
            env={**os.environ, "PGPASSWORD": settings.POSTGRES_PASSWORD},
        )

        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=f"备份失败: {result.stderr}")

        # 压缩
        shutil.make_archive(str(backup_file), "gztar", str(backup_dir), backup_file.name)
        backup_file.unlink(missing_ok=True)

        # 记录日志
        log = OperationLog(
            user_id=current_user.id,
            username=current_user.username,
            action="backup",
            module="system",
            target_desc=f"手动备份: {timestamp}",
            ip_address="system",
        )
        db.add(log)
        await db.commit()

        logger.info(f"手动备份完成: {timestamp}")
        return ResponseModel(message=f"备份完成: backup_{timestamp}.tar.gz")

    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="备份超时")
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="pg_dump 未安装")


# ============ 系统统计 ============

@router.get("/statistics", response_model=ResponseModel)
async def system_statistics(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """系统统计数据"""
    device_count = (await db.execute(select(func.count(Device.id)))).scalar() or 0
    online_count = (await db.execute(
        select(func.count(Device.id)).where(Device.status == "online")
    )).scalar() or 0
    point_count = (await db.execute(select(func.count(DataPoint.id)))).scalar() or 0
    item_count = (await db.execute(select(func.count(DataItem.id)))).scalar() or 0
    user_count = (await db.execute(select(func.count(User.id)))).scalar() or 0
    alarm_count = (await db.execute(
        select(func.count(AlarmRecord.id)).where(AlarmRecord.status == "active")
    )).scalar() or 0

    return ResponseModel(data={
        "devices": {"total": device_count, "online": online_count},
        "data_points": point_count,
        "data_items": item_count,
        "users": user_count,
        "active_alarms": alarm_count,
    })


def _parse_dt(dt_str: str) -> datetime:
    """解析日期时间"""
    try:
        if dt_str.endswith("Z"):
            dt_str = dt_str[:-1] + "+00:00"
        return datetime.fromisoformat(dt_str)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"时间格式错误: {dt_str}")
