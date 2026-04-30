# 工业数据采集管理平台 (IoT-Monitor)

基于 FastAPI + TDengine + PostgreSQL + EMQX 的工业气体监测物联网平台。

## 架构

```
┌──────────┐    ┌──────────┐    ┌──────────────────────────┐
│  DTU设备  │───▶│ TCP:9000 │───▶│                          │
└──────────┘    └──────────┘    │                          │
                                │   FastAPI Backend        │
┌──────────┐    ┌──────────┐    │   ├─ 协议解析引擎         │
│ 智能网关  │───▶│MQTT:1883 │───▶│   ├─ 数据校验引擎         │───▶ TDengine (时序数据)
│ (EMQX)   │    └──────────┘    │   ├─ 告警引擎             │───▶ PostgreSQL (业务数据)
└──────────┘                    │   ├─ WebSocket 推送       │───▶ Redis (缓存)
                                │   └─ 定时任务调度         │
┌──────────┐    ┌──────────┐    │                          │
│  前端页面  │◀──▶│ HTTP:80  │───▶│                          │
└──────────┘    └──────────┘    └──────────────────────────┘
```

## 技术栈

| 组件 | 技术 |
|------|------|
| Web 框架 | FastAPI (Python 3.11+) |
| 业务数据库 | PostgreSQL 16 |
| 时序数据库 | TDengine 3.x |
| 缓存 | Redis 7 |
| MQTT Broker | EMQX 5.x |
| 任务调度 | APScheduler |
| 认证 | JWT (python-jose) |

## 一键部署 (CentOS Stream 10)

```bash
# 克隆项目
git clone https://github.com/Luolong0223/iot-monitor.git
cd iot-monitor

# 一键部署
sudo bash deploy.sh

# 自定义配置部署
sudo DB_PASS=MySecurePass123 ADMIN_PASS=MyAdminPass456 DOMAIN=iot.example.com bash deploy.sh
```

部署完成后访问 `http://your-ip/api/docs` 查看 API 文档。

默认管理员: `admin / Admin@123456`

## 手动部署

参见 [部署文档](#部署步骤) 章节。

## API 模块

| 模块 | 路径前缀 | 功能 |
|------|----------|------|
| 认证 | /api/v1/auth | 登录、登出、Token刷新 |
| 层级管理 | /api/v1/hierarchy | 省/市/区/站点树形管理 |
| 用户管理 | /api/v1/users | 用户CRUD、重置密码 |
| 设备管理 | /api/v1/devices | 设备CRUD、状态查询、Excel导入导出 |
| 数据点管理 | /api/v1/data-points | 数据点+数据项CRUD |
| 协议管理 | /api/v1/protocols | 协议模板CRUD、测试解析 |
| 实时数据 | /api/v1/realtime | 仪表盘、实时查询 |
| 历史数据 | /api/v1/history | 聚合查询、统计、导出 |
| 告警管理 | /api/v1/alarms | 告警CRUD、配置、统计 |
| 报表 | /api/v1/reports | 日报/月报/自定义报表 |
| 系统管理 | /api/v1/system | 配置、健康检查、日志、备份 |
| WebSocket | /ws/realtime | 实时数据推送 |

## 项目结构

```
backend/
├── app/
│   ├── api/v1/           # API 路由
│   │   ├── auth.py       # 认证
│   │   ├── devices.py    # 设备管理
│   │   ├── data_points.py# 数据点管理
│   │   ├── protocols.py  # 协议管理
│   │   ├── realtime.py   # 实时数据
│   │   ├── history.py    # 历史数据
│   │   ├── alarms.py     # 告警管理
│   │   ├── reports.py    # 报表
│   │   ├── system.py     # 系统管理
│   │   └── websocket.py  # WebSocket
│   ├── core/
│   │   └── security.py   # JWT、密码加密
│   ├── models/           # SQLAlchemy 模型
│   ├── services/         # 业务服务
│   │   ├── protocol_parser.py  # 协议解析引擎
│   │   ├── data_validator.py   # 数据校验引擎
│   │   ├── tdengine_service.py # TDengine 服务
│   │   ├── alarm_engine.py     # 告警引擎
│   │   ├── scheduler.py        # 定时任务
│   │   ├── mqtt_handler.py     # MQTT 数据处理
│   │   └── tcp_handler.py      # TCP 数据处理
│   ├── mqtt/
│   │   └── client.py     # MQTT 客户端
│   ├── tcp/
│   │   └── server.py     # TCP 服务器
│   ├── config.py         # 配置管理
│   ├── database.py       # 数据库连接
│   ├── schemas.py        # Pydantic 模型
│   └── main.py           # 应用入口
├── init_db.py            # 数据库初始化脚本
└── requirements.txt
```

## 许可证

Private - Internal Use Only
