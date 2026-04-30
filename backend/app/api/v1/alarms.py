"""告警管理API"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.database import get_db
from app.models.alarm import AlarmRecord, AlarmNotification
from app.models.data_point import DataItem
from app.models.user import User
from app.schemas import AlarmAckRequest, AlarmConfigUpdate, ResponseModel
from app.core.security import get_current_user, require_admin

logger = logging.getLogger("industrial-monitor")

router = APIRouter(prefix="/alarms", tags=["告警管理"])


# ============ 告警列表 ============

@router.get("", response_model=ResponseModel)
async def list_alarms(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    alarm_type: Optional[str] = None,
    alarm_level: Optional[str] = None,
    point_id: Optional[int] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """告警列表（分页、筛选）"""
    query = select(AlarmRecord)
    count_query = select(func.count(AlarmRecord.id))

    filters = []
    if status:
        filters.append(AlarmRecord.status == status)
    if alarm_type:
        filters.append(AlarmRecord.alarm_type == alarm_type)
    if alarm_level:
        filters.append(AlarmRecord.alarm_level == alarm_level)
    if point_id is not None:
        filters.append(AlarmRecord.point_id == point_id)
    if start_time:
        filters.append(AlarmRecord.created_at >= _parse_dt(start_time))
    if end_time:
        filters.append(AlarmRecord.created_at <= _parse_dt(end_time))

    if filters:
        combined = and_(*filters)
        query = query.where(combined)
        count_query = count_query.where(combined)

    total = (await db.execute(count_query)).scalar()
    query = query.order_by(AlarmRecord.id.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    alarms = result.scalars().all()

    return ResponseModel(data={
        "list": [
            {
                "id": a.id,
                "point_id": a.point_id,
                "item_id": a.item_id,
                "alarm_type": a.alarm_type,
                "alarm_value": a.alarm_value,
                "threshold": a.threshold,
                "alarm_level": a.alarm_level,
                "status": a.status,
                "acked_by": a.acked_by,
                "acked_at": a.acked_at.isoformat() if a.acked_at else None,
                "resolved_at": a.resolved_at.isoformat() if a.resolved_at else None,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in alarms
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    })


# ============ 确认告警 ============

@router.put("/{alarm_id}/ack", response_model=ResponseModel)
async def acknowledge_alarm(
    alarm_id: int,
    req: AlarmAckRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """确认告警"""
    alarm = await db.get(AlarmRecord, alarm_id)
    if not alarm:
        raise HTTPException(status_code=404, detail="告警记录不存在")
    if alarm.status != "active":
        raise HTTPException(status_code=400, detail=f"当前状态 '{alarm.status}' 不允许确认")

    alarm.status = "acked"
    alarm.acked_by = current_user.id
    alarm.acked_at = datetime.now(timezone.utc)
    await db.commit()

    logger.info(f"告警已确认: ID={alarm_id}, 用户={current_user.username}")
    return ResponseModel(message="已确认")


# ============ 解除告警 ============

@router.put("/{alarm_id}/resolve", response_model=ResponseModel)
async def resolve_alarm(
    alarm_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """解除告警"""
    alarm = await db.get(AlarmRecord, alarm_id)
    if not alarm:
        raise HTTPException(status_code=404, detail="告警记录不存在")
    if alarm.status == "resolved":
        raise HTTPException(status_code=400, detail="告警已解除")

    alarm.status = "resolved"
    alarm.resolved_at = datetime.now(timezone.utc)
    await db.commit()

    logger.info(f"告警已解除: ID={alarm_id}, 用户={current_user.username}")
    return ResponseModel(message="已解除")


# ============ 告警统计 ============

@router.get("/statistics", response_model=ResponseModel)
async def alarm_statistics(
    start_time: Optional[str] = Query(None),
    end_time: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """告警统计"""
    base_filter = []
    if start_time:
        base_filter.append(AlarmRecord.created_at >= _parse_dt(start_time))
    if end_time:
        base_filter.append(AlarmRecord.created_at <= _parse_dt(end_time))

    combined = and_(*base_filter) if base_filter else True

    # 按状态统计
    status_stats = {}
    for s in ("active", "acked", "resolved", "suppressed"):
        count = (await db.execute(
            select(func.count(AlarmRecord.id)).where(
                AlarmRecord.status == s, combined
            )
        )).scalar() or 0
        status_stats[s] = count

    # 按级别统计
    level_stats = {}
    for level in ("warning", "critical"):
        count = (await db.execute(
            select(func.count(AlarmRecord.id)).where(
                AlarmRecord.alarm_level == level, combined
            )
        )).scalar() or 0
        level_stats[level] = count

    # 按类型统计
    type_stats = {}
    type_result = await db.execute(
        select(AlarmRecord.alarm_type, func.count(AlarmRecord.id))
        .where(combined)
        .group_by(AlarmRecord.alarm_type)
    )
    for row in type_result:
        type_stats[row[0]] = row[1]

    total = sum(status_stats.values())

    return ResponseModel(data={
        "total": total,
        "by_status": status_stats,
        "by_level": level_stats,
        "by_type": type_stats,
    })


# ============ 告警配置 CRUD ============

@router.get("/config", response_model=ResponseModel)
async def list_alarm_configs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取所有数据项的告警配置"""
    result = await db.execute(
        select(DataItem).where(DataItem.alarm_enabled == True).order_by(DataItem.id)
    )
    items = result.scalars().all()

    return ResponseModel(data=[
        {
            "item_id": item.id,
            "point_id": item.point_id,
            "item_code": item.item_code,
            "item_name": item.item_name,
            "alarm_enabled": item.alarm_enabled,
            "alarm_low": item.alarm_low,
            "alarm_high": item.alarm_high,
            "alarm_level": item.alarm_level,
        }
        for item in items
    ])


@router.put("/config/{item_id}", response_model=ResponseModel)
async def update_alarm_config(
    item_id: int,
    req: AlarmConfigUpdate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """修改数据项的告警配置"""
    item = await db.get(DataItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="数据项不存在")

    update_data = req.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(item, key, value)

    await db.commit()
    logger.info(f"告警配置更新: item_id={item_id}")
    return ResponseModel(message="配置已更新")


# ============ 告警通知配置 ============

@router.get("/notifications", response_model=ResponseModel)
async def list_alarm_notifications(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取告警通知配置"""
    result = await db.execute(select(AlarmNotification).order_by(AlarmNotification.id))
    notifications = result.scalars().all()

    return ResponseModel(data=[
        {
            "id": n.id,
            "user_id": n.user_id,
            "hierarchy_id": n.hierarchy_id,
            "notify_type": n.notify_type,
            "phone_number": n.phone_number,
            "alarm_level_filter": n.alarm_level_filter,
            "quiet_start": str(n.quiet_start) if n.quiet_start else None,
            "quiet_end": str(n.quiet_end) if n.quiet_end else None,
            "enabled": n.enabled,
        }
        for n in notifications
    ])


def _parse_dt(dt_str: Optional[str], default_days: int = 30) -> datetime:
    """解析日期时间"""
    if not dt_str:
        return datetime.now(timezone.utc) - timedelta(days=default_days)
    try:
        if dt_str.endswith("Z"):
            dt_str = dt_str[:-1] + "+00:00"
        return datetime.fromisoformat(dt_str)
    except ValueError:
        return datetime.now(timezone.utc) - timedelta(days=default_days)
