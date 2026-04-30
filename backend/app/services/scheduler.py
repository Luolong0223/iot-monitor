"""后台定时任务调度器

使用 APScheduler 实现:
- 心跳检查 (每30秒)
- 告警升级检查 (每5分钟)
- 每日备份 (配置时间)
- 日志清理 (每天)
"""
import logging
import subprocess
import os
import shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from app.config import settings

logger = logging.getLogger("industrial-monitor.scheduler")

# 全局调度器
_scheduler: Optional[AsyncIOScheduler] = None


async def heartbeat_check():
    """心跳检查: 标记超时设备为离线"""
    from app.database import async_session
    from app.models.device import Device
    from sqlalchemy import select, and_

    HEARTBEAT_TIMEOUT = timedelta(minutes=3)

    try:
        async with async_session() as db:
            # 找到心跳超时的在线设备（last_heartbeat 为 None 也视为异常）
            cutoff = datetime.now(timezone.utc) - HEARTBEAT_TIMEOUT
            result = await db.execute(
                select(Device).where(
                    and_(
                        Device.status == "online",
                        (Device.last_heartbeat < cutoff) | (Device.last_heartbeat.is_(None)),
                    )
                )
            )
            devices = result.scalars().all()

            for device in devices:
                device.status = "offline"
                logger.warning(f"设备离线: {device.device_code} (最后心跳: {device.last_heartbeat})")

                # 创建离线告警
                from app.models.data_point import DataPoint
                from app.services.alarm_engine import get_alarm_engine
                dp_result = await db.execute(
                    select(DataPoint.id).where(DataPoint.device_id == device.id)
                )
                point_ids = dp_result.scalars().all()
                alarm_engine = get_alarm_engine()
                for pid in point_ids:
                    await alarm_engine.create_offline_alarm(db, pid, device.id)

            if devices:
                await db.commit()
                logger.info(f"心跳检查: {len(devices)} 台设备标记为离线")
    except Exception as e:
        logger.error(f"心跳检查异常: {e}", exc_info=True)


async def alarm_escalation_check():
    """告警升级检查"""
    from app.database import async_session
    from app.services.alarm_engine import get_alarm_engine

    try:
        async with async_session() as db:
            alarm_engine = get_alarm_engine()
            await alarm_engine.check_escalation(db)
    except Exception as e:
        logger.error(f"告警升级检查异常: {e}", exc_info=True)


async def daily_backup():
    """每日备份"""
    try:
        backup_dir = Path(settings.BACKUP_PATH)
        backup_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"daily_backup_{timestamp}.sql"

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
            timeout=600,
            env={**os.environ, "PGPASSWORD": settings.POSTGRES_PASSWORD},
        )

        if result.returncode == 0:
            # 压缩
            shutil.make_archive(str(backup_file), "gztar", str(backup_dir), backup_file.name)
            backup_file.unlink(missing_ok=True)
            logger.info(f"每日备份完成: daily_backup_{timestamp}.tar.gz")

            # 清理旧备份
            await _cleanup_old_backups(backup_dir)
        else:
            logger.error(f"每日备份失败: {result.stderr}")
    except Exception as e:
        logger.error(f"每日备份异常: {e}", exc_info=True)


async def cleanup_old_logs():
    """清理过期操作日志 (保留最近90天)"""
    from app.database import async_session
    from app.models.system import OperationLog
    from sqlalchemy import delete

    try:
        async with async_session() as db:
            cutoff = datetime.now(timezone.utc) - timedelta(days=90)
            result = await db.execute(
                delete(OperationLog).where(OperationLog.created_at < cutoff)
            )
            await db.commit()
            if result.rowcount > 0:
                logger.info(f"清理过期日志: {result.rowcount} 条")
    except Exception as e:
        logger.error(f"清理过期日志异常: {e}", exc_info=True)


async def _cleanup_old_backups(backup_dir: Path, retain_days: int = None):
    """清理旧备份文件"""
    retain = retain_days or settings.BACKUP_RETAIN_DAYS
    cutoff = datetime.now() - timedelta(days=retain)

    for f in backup_dir.iterdir():
        if f.is_file() and f.stat().st_mtime < cutoff.timestamp():
            f.unlink()
            logger.info(f"删除过期备份: {f.name}")


def start_scheduler():
    """启动调度器"""
    global _scheduler

    if _scheduler and _scheduler.running:
        logger.warning("调度器已在运行")
        return

    _scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")

    # 心跳检查: 每30秒
    _scheduler.add_job(
        heartbeat_check,
        trigger=IntervalTrigger(seconds=30),
        id="heartbeat_check",
        name="心跳检查",
        replace_existing=True,
    )

    # 告警升级检查: 每5分钟
    _scheduler.add_job(
        alarm_escalation_check,
        trigger=IntervalTrigger(minutes=5),
        id="alarm_escalation",
        name="告警升级检查",
        replace_existing=True,
    )

    # 每日备份
    if settings.BACKUP_ENABLED:
        backup_hour, backup_minute = settings.BACKUP_TIME.split(":")
        _scheduler.add_job(
            daily_backup,
            trigger=CronTrigger(hour=int(backup_hour), minute=int(backup_minute)),
            id="daily_backup",
            name="每日备份",
            replace_existing=True,
        )

    # 日志清理: 每天凌晨3点
    _scheduler.add_job(
        cleanup_old_logs,
        trigger=CronTrigger(hour=3, minute=0),
        id="cleanup_logs",
        name="日志清理",
        replace_existing=True,
    )

    _scheduler.start()
    logger.info("定时任务调度器已启动")


def stop_scheduler():
    """停止调度器"""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("定时任务调度器已停止")


def get_scheduler_status() -> dict:
    """获取调度器状态"""
    if not _scheduler or not _scheduler.running:
        return {"running": False, "jobs": []}

    jobs = []
    for job in _scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
        })

    return {"running": True, "jobs": jobs}
