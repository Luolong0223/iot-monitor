"""实时数据API"""
import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models.data_point import DataPoint, DataItem
from app.models.device import Device
from app.models.alarm import AlarmRecord
from app.models.hierarchy import HierarchyLevel
from app.models.user import User
from app.schemas import ResponseModel
from app.core.security import get_current_user
from app.services.tdengine_service import get_tdengine_service

logger = logging.getLogger("industrial-monitor")

router = APIRouter(prefix="/realtime", tags=["实时数据"])


@router.get("/overview", response_model=ResponseModel)
async def realtime_overview(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """仪表盘概览统计"""
    # 设备统计
    total_devices = (await db.execute(select(func.count(Device.id)))).scalar() or 0
    online_devices = (await db.execute(
        select(func.count(Device.id)).where(Device.status == "online")
    )).scalar() or 0
    offline_devices = (await db.execute(
        select(func.count(Device.id)).where(Device.status == "offline")
    )).scalar() or 0
    maintenance_devices = (await db.execute(
        select(func.count(Device.id)).where(Device.status == "maintenance")
    )).scalar() or 0

    # 数据点统计
    total_points = (await db.execute(select(func.count(DataPoint.id)))).scalar() or 0
    active_points = (await db.execute(
        select(func.count(DataPoint.id)).where(DataPoint.status == "active")
    )).scalar() or 0

    # 告警统计
    active_alarms = (await db.execute(
        select(func.count(AlarmRecord.id)).where(AlarmRecord.status == "active")
    )).scalar() or 0
    critical_alarms = (await db.execute(
        select(func.count(AlarmRecord.id)).where(
            AlarmRecord.status == "active",
            AlarmRecord.alarm_level == "critical",
        )
    )).scalar() or 0

    # 数据项总数
    total_items = (await db.execute(select(func.count(DataItem.id)))).scalar() or 0

    return ResponseModel(data={
        "devices": {
            "total": total_devices,
            "online": online_devices,
            "offline": offline_devices,
            "maintenance": maintenance_devices,
        },
        "data_points": {
            "total": total_points,
            "active": active_points,
        },
        "data_items": {
            "total": total_items,
        },
        "alarms": {
            "active": active_alarms,
            "critical": critical_alarms,
        },
    })


@router.get("/point/{point_id}", response_model=ResponseModel)
async def realtime_point(
    point_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """单个数据点实时数据"""
    point = await db.get(DataPoint, point_id)
    if not point:
        raise HTTPException(status_code=404, detail="数据点不存在")

    tdengine = get_tdengine_service()
    items_data = []

    for item in (point.items or []):
        latest = tdengine.query_latest(point_id, item.id) if tdengine.connected else None
        items_data.append({
            "item_id": item.id,
            "item_code": item.item_code,
            "item_name": item.item_name,
            "unit": item.unit,
            "data_type": item.data_type,
            "value": latest.get("value") if latest else None,
            "timestamp": latest.get("timestamp") if latest else None,
            "quality": latest.get("quality", 0) if latest else 0,
        })

    return ResponseModel(data={
        "point_id": point.id,
        "point_code": point.point_code,
        "point_name": point.point_name,
        "status": point.status,
        "items": items_data,
    })


@router.get("/hierarchy/{hierarchy_id}", response_model=ResponseModel)
async def realtime_hierarchy(
    hierarchy_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """层级子树实时数据"""
    # 获取层级节点
    node = await db.get(HierarchyLevel, hierarchy_id)
    if not node:
        raise HTTPException(status_code=404, detail="层级节点不存在")

    # 递归获取所有子节点ID
    all_ids = await _get_hierarchy_ids(db, hierarchy_id)

    # 查询这些层级下的数据点
    result = await db.execute(
        select(DataPoint).where(DataPoint.hierarchy_id.in_(all_ids))
    )
    points = result.scalars().all()

    tdengine = get_tdengine_service()
    points_data = []

    for point in points:
        items_data = []
        for item in (point.items or []):
            latest = tdengine.query_latest(point.id, item.id) if tdengine.connected else None
            items_data.append({
                "item_id": item.id,
                "item_code": item.item_code,
                "item_name": item.item_name,
                "unit": item.unit,
                "value": latest.get("value") if latest else None,
                "timestamp": latest.get("timestamp") if latest else None,
            })
        points_data.append({
            "point_id": point.id,
            "point_code": point.point_code,
            "point_name": point.point_name,
            "status": point.status,
            "items": items_data,
        })

    return ResponseModel(data={
        "hierarchy_id": hierarchy_id,
        "hierarchy_name": node.name,
        "point_count": len(points_data),
        "points": points_data,
    })


async def _get_hierarchy_ids(db: AsyncSession, node_id: int) -> List[int]:
    """递归获取层级节点及所有子节点ID"""
    ids = [node_id]
    result = await db.execute(
        select(HierarchyLevel.id).where(HierarchyLevel.parent_id == node_id)
    )
    children = result.scalars().all()
    for child_id in children:
        child_ids = await _get_hierarchy_ids(db, child_id)
        ids.extend(child_ids)
    return ids
