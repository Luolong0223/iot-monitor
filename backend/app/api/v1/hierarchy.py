"""层级管理API"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from app.database import get_db
from app.models.hierarchy import HierarchyLevel
from app.models.user import User
from app.schemas import HierarchyCreate, HierarchyUpdate, ResponseModel
from app.core.security import get_current_user, require_admin

router = APIRouter(prefix="/hierarchy", tags=["层级管理"])


def build_tree(nodes, parent_id=None):
    """递归构建层级树"""
    tree = []
    for node in nodes:
        if node.parent_id == parent_id:
            children = build_tree(nodes, node.id)
            tree.append({
                "id": node.id,
                "name": node.name,
                "parent_id": node.parent_id,
                "level_type": node.level_type,
                "sort_order": node.sort_order,
                "description": node.description,
                "created_at": str(node.created_at),
                "children": children,
            })
    tree.sort(key=lambda x: x["sort_order"])
    return tree


@router.get("/tree", response_model=ResponseModel)
async def get_hierarchy_tree(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取完整层级树"""
    result = await db.execute(select(HierarchyLevel))
    nodes = result.scalars().all()
    tree = build_tree(nodes)
    return ResponseModel(data=tree)


@router.post("", response_model=ResponseModel)
async def create_hierarchy(
    req: HierarchyCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """新增层级节点"""
    # 验证父节点存在
    if req.parent_id:
        parent = await db.get(HierarchyLevel, req.parent_id)
        if not parent:
            raise HTTPException(status_code=400, detail="父级节点不存在")

    node = HierarchyLevel(
        name=req.name,
        parent_id=req.parent_id,
        level_type=req.level_type,
        sort_order=req.sort_order,
        description=req.description,
    )
    db.add(node)
    await db.flush()
    await db.refresh(node)

    return ResponseModel(data={"id": node.id}, message="创建成功")


@router.put("/{node_id}", response_model=ResponseModel)
async def update_hierarchy(
    node_id: int,
    req: HierarchyUpdate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """修改层级节点"""
    node = await db.get(HierarchyLevel, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="节点不存在")

    # 不能把节点设为自己的子节点
    if req.parent_id == node_id:
        raise HTTPException(status_code=400, detail="不能将节点设为自己的子节点")

    update_data = req.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(node, key, value)

    await db.commit()
    return ResponseModel(message="修改成功")


@router.delete("/{node_id}", response_model=ResponseModel)
async def delete_hierarchy(
    node_id: int,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """删除层级节点"""
    node = await db.get(HierarchyLevel, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="节点不存在")

    # 检查是否有子节点
    result = await db.execute(
        select(HierarchyLevel).where(HierarchyLevel.parent_id == node_id)
    )
    children = result.scalars().all()
    if children:
        raise HTTPException(status_code=400, detail="该节点下有子节点，无法删除")

    # 检查是否有关联设备或用户
    # TODO: 添加关联检查

    await db.delete(node)
    await db.commit()
    return ResponseModel(message="删除成功")


@router.get("/{node_id}/children", response_model=ResponseModel)
async def get_children(
    node_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取子节点列表"""
    result = await db.execute(
        select(HierarchyLevel)
        .where(HierarchyLevel.parent_id == node_id)
        .order_by(HierarchyLevel.sort_order)
    )
    nodes = result.scalars().all()
    return ResponseModel(data=[
        {
            "id": n.id,
            "name": n.name,
            "parent_id": n.parent_id,
            "level_type": n.level_type,
            "sort_order": n.sort_order,
            "description": n.description,
        }
        for n in nodes
    ])
