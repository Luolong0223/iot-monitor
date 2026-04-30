"""历史数据API"""
import logging
from io import BytesIO
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from openpyxl import Workbook

from app.database import get_db
from app.models.data_point import DataPoint, DataItem
from app.models.user import User
from app.schemas import ResponseModel
from app.core.security import get_current_user
from app.services.tdengine_service import get_tdengine_service

logger = logging.getLogger("industrial-monitor")

router = APIRouter(prefix="/history", tags=["历史数据"])


@router.get("/query", response_model=ResponseModel)
async def query_history(
    point_id: int = Query(..., description="数据点ID"),
    item_id: int = Query(..., description="数据项ID"),
    start_time: Optional[str] = Query(None, description="开始时间 ISO格式"),
    end_time: Optional[str] = Query(None, description="结束时间 ISO格式"),
    aggregation: Optional[str] = Query(None, description="聚合函数: avg/max/min/sum/count"),
    interval: Optional[str] = Query(None, description="聚合间隔: 1m/5m/1h/1d"),
    limit: int = Query(10000, ge=1, le=100000),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """查询历史数据"""
    # 验证数据点和数据项
    point = await db.get(DataPoint, point_id)
    if not point:
        raise HTTPException(status_code=404, detail="数据点不存在")

    item = await db.get(DataItem, item_id)
    if not item or item.point_id != point_id:
        raise HTTPException(status_code=404, detail="数据项不存在")

    # 默认时间范围: 最近24小时
    now = datetime.now(timezone.utc)
    start = _parse_datetime(start_time, now - timedelta(hours=24))
    end = _parse_datetime(end_time, now)

    tdengine = get_tdengine_service()
    if not tdengine.connected:
        raise HTTPException(status_code=503, detail="时序数据库未连接")

    data = tdengine.query_history(
        point_id=point_id,
        item_id=item_id,
        start_time=start,
        end_time=end,
        aggregation=aggregation,
        interval=interval,
        limit=limit,
    )

    return ResponseModel(data={
        "point_id": point_id,
        "item_id": item_id,
        "item_name": item.item_name,
        "unit": item.unit,
        "aggregation": aggregation,
        "interval": interval,
        "start_time": start.isoformat(),
        "end_time": end.isoformat(),
        "count": len(data),
        "list": data,
    })


@router.get("/statistics", response_model=ResponseModel)
async def history_statistics(
    point_id: int = Query(...),
    item_id: int = Query(...),
    start_time: Optional[str] = Query(None),
    end_time: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """历史数据统计"""
    point = await db.get(DataPoint, point_id)
    if not point:
        raise HTTPException(status_code=404, detail="数据点不存在")

    item = await db.get(DataItem, item_id)
    if not item or item.point_id != point_id:
        raise HTTPException(status_code=404, detail="数据项不存在")

    now = datetime.now(timezone.utc)
    start = _parse_datetime(start_time, now - timedelta(hours=24))
    end = _parse_datetime(end_time, now)

    tdengine = get_tdengine_service()
    if not tdengine.connected:
        raise HTTPException(status_code=503, detail="时序数据库未连接")

    stats = tdengine.query_statistics(point_id, item_id, start, end)

    return ResponseModel(data={
        "point_id": point_id,
        "item_id": item_id,
        "item_name": item.item_name,
        "unit": item.unit,
        "start_time": start.isoformat(),
        "end_time": end.isoformat(),
        "statistics": stats,
    })


@router.get("/export")
async def export_history(
    point_id: int = Query(...),
    item_id: int = Query(...),
    start_time: Optional[str] = Query(None),
    end_time: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """导出历史数据到Excel"""
    point = await db.get(DataPoint, point_id)
    if not point:
        raise HTTPException(status_code=404, detail="数据点不存在")

    item = await db.get(DataItem, item_id)
    if not item or item.point_id != point_id:
        raise HTTPException(status_code=404, detail="数据项不存在")

    now = datetime.now(timezone.utc)
    start = _parse_datetime(start_time, now - timedelta(hours=24))
    end = _parse_datetime(end_time, now)

    tdengine = get_tdengine_service()
    if not tdengine.connected:
        raise HTTPException(status_code=503, detail="时序数据库未连接")

    data = tdengine.export_data(point_id, item_id, start, end)

    wb = Workbook()
    ws = wb.active
    ws.title = "历史数据"

    headers = ["时间", f"值({item.unit or ''})", "质量码"]
    ws.append(headers)

    for row in data:
        ws.append([
            row.get("timestamp", ""),
            row.get("value", ""),
            row.get("quality", 0),
        ])

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    wb.close()

    filename = f"history_{point.point_code}_{item.item_code}.xlsx"
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


def _parse_datetime(dt_str: Optional[str], default: datetime) -> datetime:
    """解析日期时间字符串"""
    if not dt_str:
        return default
    try:
        # 尝试ISO格式
        if dt_str.endswith("Z"):
            dt_str = dt_str[:-1] + "+00:00"
        return datetime.fromisoformat(dt_str)
    except ValueError:
        return default
