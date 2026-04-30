#!/usr/bin/env python3
"""
数据库初始化脚本

功能:
1. 创建所有数据库表
2. 初始化系统配置
3. 创建默认超级管理员账号
4. 创建内置协议模板

使用: python init_db.py
"""
import asyncio
import sys
import os

# 确保从 backend 目录运行
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import engine, async_session, Base
from app.models import *  # noqa: 触发所有模型注册
from app.core.security import hash_password
from app.models.system import SystemConfig, OperationLog
from app.models.user import User
from app.models.protocol import ProtocolTemplate


async def create_tables():
    """创建所有表"""
    print("📦 创建数据库表...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ 数据库表创建完成")


async def seed_system_config():
    """初始化系统配置"""
    print("⚙️  初始化系统配置...")
    async with async_session() as db:
        configs = [
            SystemConfig(
                config_key="system.name",
                config_value="工业数据采集管理平台",
                config_group="system",
                value_type="string",
                description="系统名称",
            ),
            SystemConfig(
                config_key="alarm.suppression_minutes",
                config_value="5",
                config_group="alarm",
                value_type="number",
                description="告警抑制时间(分钟)",
            ),
            SystemConfig(
                config_key="alarm.escalation_warning",
                config_value="15,30,60",
                config_group="alarm",
                value_type="string",
                description="warning级别升级阈值(分钟)",
            ),
            SystemConfig(
                config_key="alarm.escalation_critical",
                config_value="10,20,40",
                config_group="alarm",
                value_type="string",
                description="critical级别升级阈值(分钟)",
            ),
            SystemConfig(
                config_key="heartbeat.timeout_minutes",
                config_value="3",
                config_group="device",
                value_type="number",
                description="心跳超时时间(分钟)",
            ),
            SystemConfig(
                config_key="data.cleanup_days",
                config_value="90",
                config_group="data",
                value_type="number",
                description="操作日志保留天数",
            ),
            SystemConfig(
                config_key="backup.enabled",
                config_value="true",
                config_group="backup",
                value_type="boolean",
                description="是否启用自动备份",
            ),
            SystemConfig(
                config_key="backup.time",
                config_value="02:00",
                config_group="backup",
                value_type="string",
                description="自动备份时间",
            ),
            SystemConfig(
                config_key="backup.retain_days",
                config_value="30",
                config_group="backup",
                value_type="number",
                description="备份保留天数",
            ),
        ]

        for config in configs:
            # 跳过已存在的配置
            from sqlalchemy import select
            existing = await db.execute(
                select(SystemConfig).where(SystemConfig.config_key == config.config_key)
            )
            if existing.scalar_one_or_none():
                continue
            db.add(config)

        await db.commit()
    print("✅ 系统配置初始化完成")


async def create_admin_user():
    """创建默认超级管理员"""
    print("👤 创建默认管理员账号...")
    async with async_session() as db:
        from sqlalchemy import select

        # 检查是否已有管理员
        result = await db.execute(
            select(User).where(User.role == "superadmin")
        )
        if result.scalar_one_or_none():
            print("⏭️  已存在超级管理员，跳过")
            return

        admin = User(
            username="admin",
            password_hash=hash_password("Admin@123456"),
            real_name="系统管理员",
            role="superadmin",
            status="active",
        )
        db.add(admin)
        await db.commit()
        print("✅ 默认管理员创建完成")
        print("   用户名: admin")
        print("   密  码: Admin@123456")
        print("   ⚠️  请登录后立即修改密码!")


async def seed_builtin_protocols():
    """创建内置协议模板"""
    print("📋 创建内置协议模板...")
    async with async_session() as db:
        from sqlalchemy import select

        protocols = [
            ProtocolTemplate(
                template_name="Modbus RTU - 标准气体传感器",
                description="Modbus RTU协议，适用于标准气体浓度传感器，功能码03读保持寄存器",
                protocol_type="modbus_rtu",
                frame_format={
                    "slave_id": 1,
                    "function_code": 3,
                    "registers": [
                        {"name": "methane", "address": 0, "count": 1, "data_type": "uint16", "scale": 0.01, "offset_value": 0},
                        {"name": "oxygen", "address": 1, "count": 1, "data_type": "uint16", "scale": 0.1, "offset_value": 0},
                        {"name": "co", "address": 2, "count": 1, "data_type": "uint16", "scale": 1, "offset_value": 0},
                        {"name": "temperature", "address": 3, "count": 1, "data_type": "int16", "scale": 0.1, "offset_value": 0},
                        {"name": "humidity", "address": 4, "count": 1, "data_type": "uint16", "scale": 0.1, "offset_value": 0},
                    ],
                },
                is_builtin=True,
            ),
            ProtocolTemplate(
                template_name="自定义帧 - AA55帧头",
                description="自定义协议格式，AA55帧头，含CRC16校验",
                protocol_type="custom_frame",
                frame_format={
                    "header": {"offset": 0, "length": 2, "value": "AA55"},
                    "length_field": {"offset": 2, "length": 1},
                    "data_items": [
                        {"name": "methane", "offset": 4, "length": 2, "data_type": "uint16", "byte_order": "big_endian", "scale": 0.01, "offset_value": 0},
                        {"name": "temperature", "offset": 6, "length": 2, "data_type": "int16", "byte_order": "big_endian", "scale": 0.1, "offset_value": 0},
                    ],
                    "checksum": {"type": "crc16", "offset": -2},
                },
                is_builtin=True,
            ),
            ProtocolTemplate(
                template_name="JSON - 标准格式",
                description="JSON格式数据上报，适用于智能网关设备",
                protocol_type="json",
                frame_format={
                    "encoding": "utf-8",
                    "field_mapping": [
                        {"json_path": "methane", "name": "methane", "scale": 1.0, "offset_value": 0},
                        {"json_path": "oxygen", "name": "oxygen", "scale": 1.0, "offset_value": 0},
                        {"json_path": "temperature", "name": "temperature", "scale": 1.0, "offset_value": 0},
                        {"json_path": "humidity", "name": "humidity", "scale": 1.0, "offset_value": 0},
                    ],
                },
                is_builtin=True,
            ),
        ]

        for proto in protocols:
            existing = await db.execute(
                select(ProtocolTemplate).where(ProtocolTemplate.template_name == proto.template_name)
            )
            if existing.scalar_one_or_none():
                continue
            db.add(proto)

        await db.commit()
    print("✅ 内置协议模板创建完成")


async def main():
    print("=" * 50)
    print("  工业数据采集管理平台 - 数据库初始化")
    print("=" * 50)
    print()

    try:
        await create_tables()
        await seed_system_config()
        await create_admin_user()
        await seed_builtin_protocols()

        print()
        print("=" * 50)
        print("  ✅ 初始化完成!")
        print("=" * 50)
        print()
        print("  下一步:")
        print("  1. 启动后端: python -m uvicorn app.main:app --host 0.0.0.0 --port 8000")
        print("  2. 访问文档: http://your-ip:8000/api/docs")
        print("  3. 使用 admin / Admin@123456 登录")
        print("  4. 立即修改默认密码!")
        print()

    except Exception as e:
        print(f"\n❌ 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
