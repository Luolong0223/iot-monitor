"""认证API"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.user import User
from app.schemas import LoginRequest, LoginResponse, ChangePasswordRequest, ResponseModel, RefreshRequest
from app.core.security import (
    verify_password, hash_password, create_access_token,
    create_refresh_token, decode_token, get_current_user,
)

router = APIRouter(prefix="/auth", tags=["认证模块"])


@router.post("/login", response_model=ResponseModel)
async def login(req: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """用户登录"""
    result = await db.execute(select(User).where(User.username == req.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    if user.status == "disabled":
        raise HTTPException(status_code=403, detail="账号已被禁用")

    # 检查锁定
    if user.locked_until and user.locked_until > datetime.now(timezone.utc):
        raise HTTPException(status_code=403, detail=f"账号已锁定，请稍后再试")

    # 重置登录失败次数
    user.login_attempts = 0
    user.locked_until = None
    user.last_login = datetime.now(timezone.utc)

    # 生成Token
    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})

    await db.commit()

    return ResponseModel(data={
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": 7200,
        "user": {
            "id": user.id,
            "username": user.username,
            "real_name": user.real_name,
            "role": user.role,
            "hierarchy_id": user.hierarchy_id,
        }
    })


@router.post("/refresh", response_model=ResponseModel)
async def refresh_token(req: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """刷新Token"""
    payload = decode_token(req.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="无效的刷新Token")

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if not user or user.status == "disabled":
        raise HTTPException(status_code=401, detail="用户不存在或已禁用")

    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})

    return ResponseModel(data={
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": 7200,
    })


@router.get("/me", response_model=ResponseModel)
async def get_me(current_user: User = Depends(get_current_user)):
    """获取当前用户信息"""
    return ResponseModel(data={
        "id": current_user.id,
        "username": current_user.username,
        "real_name": current_user.real_name,
        "phone": current_user.phone,
        "email": current_user.email,
        "role": current_user.role,
        "hierarchy_id": current_user.hierarchy_id,
        "status": current_user.status,
        "last_login": str(current_user.last_login) if current_user.last_login else None,
    })


@router.put("/password", response_model=ResponseModel)
async def change_password(
    req: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """修改密码"""
    if not verify_password(req.old_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="原密码错误")

    current_user.password_hash = hash_password(req.new_password)
    await db.commit()

    return ResponseModel(message="密码修改成功")


@router.post("/logout", response_model=ResponseModel)
async def logout(current_user: User = Depends(get_current_user)):
    """登出（前端清除Token即可，服务端可选加Token黑名单）"""
    return ResponseModel(message="已登出")
