"""用户模型"""
from sqlalchemy import Column, Integer, String, Boolean, TIMESTAMP, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, comment="用户名")
    password_hash = Column(String(200), nullable=False, comment="密码hash")
    real_name = Column(String(100), comment="真实姓名")
    phone = Column(String(20), comment="手机号")
    email = Column(String(100), comment="邮箱")
    role = Column(String(20), default="user", comment="角色: superadmin/admin/user/readonly")
    hierarchy_id = Column(Integer, ForeignKey("hierarchy_levels.id"), comment="绑定层级")
    status = Column(String(20), default="active", comment="状态: active/disabled")
    last_login = Column(TIMESTAMP, comment="最后登录时间")
    login_attempts = Column(Integer, default=0, comment="连续登录失败次数")
    locked_until = Column(TIMESTAMP, comment="锁定截止时间")
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    # 关系
    hierarchy = relationship("HierarchyLevel", back_populates="users")
