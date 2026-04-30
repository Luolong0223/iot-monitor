"""用户管理API"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from app.database import get_db
from app.models.user import User
from app.schemas import UserCreate, UserUpdate, ResponseModel
from app.core.security import get_current_user, require_admin, hash_password

router = APIRouter(prefix="/users", tags=["用户管理"])


@router.get("", response_model=ResponseModel)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: Optional[str] = None,
    role: Optional[str] = None,
    status: Optional[str] = None,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """用户列表"""
    query = select(User)
    count_query = select(func.count(User.id))

    if keyword:
        filter_cond = User.username.contains(keyword) | User.real_name.contains(keyword)
        query = query.where(filter_cond)
        count_query = count_query.where(filter_cond)
    if role:
        query = query.where(User.role == role)
        count_query = count_query.where(User.role == role)
    if status:
        query = query.where(User.status == status)
        count_query = count_query.where(User.status == status)

    # 总数
    total = (await db.execute(count_query)).scalar()

    # 分页
    query = query.order_by(User.id).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    users = result.scalars().all()

    return ResponseModel(data={
        "list": [
            {
                "id": u.id,
                "username": u.username,
                "real_name": u.real_name,
                "phone": u.phone,
                "email": u.email,
                "role": u.role,
                "hierarchy_id": u.hierarchy_id,
                "status": u.status,
                "last_login": str(u.last_login) if u.last_login else None,
                "created_at": str(u.created_at),
            }
            for u in users
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    })


@router.post("", response_model=ResponseModel)
async def create_user(
    req: UserCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """新增用户"""
    # 检查用户名是否已存在
    existing = await db.execute(select(User).where(User.username == req.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="用户名已存在")

    user = User(
        username=req.username,
        password_hash=hash_password(req.password),
        real_name=req.real_name,
        phone=req.phone,
        email=req.email,
        role=req.role,
        hierarchy_id=req.hierarchy_id,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)

    return ResponseModel(data={"id": user.id}, message="创建成功")


@router.put("/{user_id}", response_model=ResponseModel)
async def update_user(
    user_id: int,
    req: UserUpdate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """修改用户"""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    update_data = req.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(user, key, value)

    await db.commit()
    return ResponseModel(message="修改成功")


@router.delete("/{user_id}", response_model=ResponseModel)
async def delete_user(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """删除用户（软删除）"""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="不能删除自己")

    user.status = "disabled"
    await db.commit()
    return ResponseModel(message="已禁用")


@router.put("/{user_id}/reset-password", response_model=ResponseModel)
async def reset_password(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """重置密码（默认密码：IoT@123456）"""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    user.password_hash = hash_password("IoT@123456")
    user.login_attempts = 0
    user.locked_until = None
    await db.commit()

    return ResponseModel(message="密码已重置为 IoT@123456")
