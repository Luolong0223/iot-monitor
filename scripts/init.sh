#!/bin/bash
# ============================================
# 项目初始化脚本
# ============================================

set -e

echo "=== 工业数据采集管理平台 - 初始化 ==="

# 1. 复制环境变量
if [ ! -f .env ]; then
    cp .env.example .env
    echo "✅ 已创建 .env 文件，请修改数据库密码等配置"
else
    echo "⏭️  .env 文件已存在，跳过"
fi

# 2. 创建必要目录
mkdir -p logs backup ssl
echo "✅ 已创建 logs/backup/ssl 目录"

# 3. 启动服务
echo "🚀 启动 Docker Compose 服务..."
docker compose up -d

# 4. 等待数据库就绪
echo "⏳ 等待 PostgreSQL 就绪..."
sleep 10

# 5. 执行初始化SQL
echo "📦 执行数据库初始化..."
docker compose exec -T postgres psql -U postgres -d iot_db -f /backup/init_db.sql 2>/dev/null || echo "⚠️  初始化SQL执行失败，请手动执行"

# 6. 创建默认管理员
echo "👤 创建默认管理员账号..."
docker compose exec backend python -c "
from app.core.security import hash_password
import asyncio
async def create_admin():
    from app.database import async_session, init_db
    from app.models.user import User
    from sqlalchemy import select
    await init_db()
    async with async_session() as db:
        result = await db.execute(select(User).where(User.username == 'admin'))
        if not result.scalar_one_or_none():
            admin = User(
                username='admin',
                password_hash=hash_password('Admin@123456'),
                real_name='系统管理员',
                role='superadmin',
                status='active',
            )
            db.add(admin)
            await db.commit()
            print('✅ 默认管理员已创建: admin / Admin@123456')
        else:
            print('⏭️  管理员已存在')
asyncio.run(create_admin())
" 2>/dev/null || echo "⚠️  管理员创建失败，请手动创建"

echo ""
echo "=== 初始化完成 ==="
echo "📊 管理后台: http://localhost"
echo "📖 API文档: http://localhost:8000/api/docs"
echo "🔑 默认账号: admin / Admin@123456"
echo "📡 EMQX控制台: http://localhost:18083"
echo ""
echo "⚠️  请务必修改 .env 中的数据库密码和JWT密钥！"
