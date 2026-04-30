"""协议管理API"""
import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from io import BytesIO
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models.protocol import ProtocolTemplate
from app.models.user import User
from app.schemas import ProtocolCreate, ProtocolUpdate, ProtocolTestRequest, ResponseModel
from app.core.security import get_current_user, require_admin

logger = logging.getLogger("industrial-monitor")

router = APIRouter(prefix="/protocols", tags=["协议管理"])


# ============ 列表 ============

@router.get("", response_model=ResponseModel)
async def list_protocols(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: Optional[str] = None,
    protocol_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """协议模板列表"""
    query = select(ProtocolTemplate)
    count_query = select(func.count(ProtocolTemplate.id))

    if keyword:
        like_pattern = f"%{keyword}%"
        query = query.where(ProtocolTemplate.template_name.ilike(like_pattern))
        count_query = count_query.where(ProtocolTemplate.template_name.ilike(like_pattern))
    if protocol_type:
        query = query.where(ProtocolTemplate.protocol_type == protocol_type)
        count_query = count_query.where(ProtocolTemplate.protocol_type == protocol_type)

    total = (await db.execute(count_query)).scalar()
    query = query.order_by(ProtocolTemplate.id.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    templates = result.scalars().all()

    return ResponseModel(data={
        "list": [
            {
                "id": t.id,
                "template_name": t.template_name,
                "description": t.description,
                "protocol_type": t.protocol_type,
                "is_builtin": t.is_builtin,
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "updated_at": t.updated_at.isoformat() if t.updated_at else None,
            }
            for t in templates
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    })


# ============ 详情 ============

@router.get("/{template_id}", response_model=ResponseModel)
async def get_protocol(
    template_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """协议模板详情（含frame_format）"""
    template = await db.get(ProtocolTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="协议模板不存在")

    return ResponseModel(data={
        "id": template.id,
        "template_name": template.template_name,
        "description": template.description,
        "protocol_type": template.protocol_type,
        "frame_format": template.frame_format,
        "is_builtin": template.is_builtin,
        "created_at": template.created_at.isoformat() if template.created_at else None,
        "updated_at": template.updated_at.isoformat() if template.updated_at else None,
    })


# ============ 新增 ============

@router.post("", response_model=ResponseModel)
async def create_protocol(
    req: ProtocolCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """新增协议模板"""
    template = ProtocolTemplate(
        template_name=req.template_name,
        description=req.description,
        protocol_type=req.protocol_type,
        frame_format=req.frame_format,
    )
    db.add(template)
    await db.flush()
    await db.refresh(template)
    logger.info(f"新增协议模板: {template.template_name} (ID={template.id})")

    return ResponseModel(data={"id": template.id}, message="创建成功")


# ============ 修改 ============

@router.put("/{template_id}", response_model=ResponseModel)
async def update_protocol(
    template_id: int,
    req: ProtocolUpdate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """修改协议模板"""
    template = await db.get(ProtocolTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="协议模板不存在")
    if template.is_builtin:
        raise HTTPException(status_code=400, detail="内置模板不可修改")

    update_data = req.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(template, key, value)

    await db.commit()
    logger.info(f"修改协议模板: ID={template_id}")
    return ResponseModel(message="修改成功")


# ============ 删除 ============

@router.delete("/{template_id}", response_model=ResponseModel)
async def delete_protocol(
    template_id: int,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """删除协议模板"""
    template = await db.get(ProtocolTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="协议模板不存在")
    if template.is_builtin:
        raise HTTPException(status_code=400, detail="内置模板不可删除")

    await db.delete(template)
    await db.commit()
    logger.info(f"删除协议模板: ID={template_id}")
    return ResponseModel(message="删除成功")


# ============ 测试解析 ============

@router.post("/test-parse", response_model=ResponseModel)
async def test_parse(
    req: ProtocolTestRequest,
    current_user: User = Depends(get_current_user),
):
    """测试协议解析：传入协议配置和十六进制报文，返回解析结果"""
    try:
        from app.services.protocol_parser import ProtocolParser
        parser = ProtocolParser()
        result = parser.parse(
            protocol_type=req.protocol_type,
            frame_format=req.frame_format,
            hex_data=req.test_data,
        )
        return ResponseModel(data=result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"解析错误: {str(e)}")
    except Exception as e:
        logger.error(f"协议解析测试失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"解析异常: {str(e)}")


# ============ 导出为JSON ============

@router.get("/{template_id}/export", response_model=None)
async def export_protocol(
    template_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """导出协议模板为JSON"""
    template = await db.get(ProtocolTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="协议模板不存在")

    export_data = {
        "template_name": template.template_name,
        "description": template.description,
        "protocol_type": template.protocol_type,
        "frame_format": template.frame_format,
        "version": "1.0",
    }

    content = json.dumps(export_data, ensure_ascii=False, indent=2)
    output = BytesIO(content.encode("utf-8"))

    return StreamingResponse(
        output,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename=protocol_{template_id}.json'
        },
    )


# ============ 从JSON导入 ============

@router.post("/import", response_model=ResponseModel)
async def import_protocol(
    req: dict,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """从JSON导入协议模板"""
    required_fields = ["template_name", "protocol_type", "frame_format"]
    for field in required_fields:
        if field not in req:
            raise HTTPException(status_code=400, detail=f"缺少必填字段: {field}")

    template = ProtocolTemplate(
        template_name=req["template_name"],
        description=req.get("description", ""),
        protocol_type=req["protocol_type"],
        frame_format=req["frame_format"],
    )
    db.add(template)
    await db.flush()
    await db.refresh(template)
    logger.info(f"导入协议模板: {template.template_name} (ID={template.id})")

    return ResponseModel(data={"id": template.id}, message="导入成功")
