# 贵阳燃气外围数据采集管理平台

## 项目简介

覆盖贵州省多个地级市的燃气数据采集管理平台，支持1000+数据点位接入，提供实时监控、历史查询、告警管理、报表导出等完整功能。

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3 + Element Plus + ECharts + Vite |
| 后端 | Python FastAPI + SQLAlchemy 2.0 |
| 时序库 | TDengine 3.x |
| 业务库 | PostgreSQL 16 |
| 消息中间件 | EMQX 5.x (MQTT Broker) |
| 缓存 | Redis 7 |
| 部署 | Docker Compose + Nginx |

## 快速开始

### 环境要求

- Docker 20.10+
- Docker Compose 2.0+

### 启动

```bash
# 1. 克隆项目
git clone https://github.com/Luolong0223/iot-monitor.git
cd iot-monitor

# 2. 复制环境变量并修改
cp .env.example .env
# 编辑 .env 修改数据库密码等配置

# 3. 一键启动
docker compose up -d

# 4. 初始化数据库和默认管理员
bash scripts/init.sh
```

### 访问

| 服务 | 地址 |
|------|------|
| 管理后台 | http://localhost |
| API文档 | http://localhost:8000/api/docs |
| EMQX控制台 | http://localhost:18083 |
| 默认账号 | admin / Admin@123456 |

## 项目结构

```
iot-monitor/
├── docker-compose.yml          # Docker编排
├── .env.example                # 环境变量模板
├── nginx/nginx.conf            # Nginx配置
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py             # FastAPI入口（集成MQTT/TCP/调度器）
│       ├── config.py           # 配置管理
│       ├── database.py         # 数据库连接
│       ├── schemas.py          # 数据模型
│       ├── models/             # ORM模型（10张表）
│       ├── api/v1/             # API路由（12个模块）
│       ├── core/               # 核心模块(JWT/RBAC)
│       ├── services/           # 业务逻辑（7个服务）
│       ├── mqtt/               # MQTT客户端
│       ├── tcp/                # TCP服务器
│       └── utils/              # 工具函数
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── api/                # API调用封装（13个模块）
│       ├── stores/             # Pinia状态管理
│       ├── router/             # Vue Router
│       ├── layouts/            # 布局组件
│       ├── views/              # 页面（15个视图）
│       ├── utils/              # 工具函数
│       └── main.js
├── scripts/                    # 初始化脚本
└── backup/                     # 备份目录
```

## 开发进度

### 后端

- [x] 项目骨架搭建
- [x] 数据库模型设计（10张表）
- [x] 用户认证（JWT + RBAC）
- [x] 层级管理API
- [x] 用户管理API
- [x] 设备管理API（CRUD + Excel导入导出）
- [x] 数据点管理API（含数据项CRUD）
- [x] 协议管理API（CRUD + 测试解析 + 导入导出）
- [x] 协议解析引擎（Modbus RTU/TCP、自定义帧、JSON、CSV）
- [x] 数据校验清洗引擎（范围/突变/零值/重复检测）
- [x] MQTT数据接收服务（EMQX集成）
- [x] TCP数据接收服务（异步Socket）
- [x] TDengine时序数据服务（写入/查询/聚合）
- [x] WebSocket实时推送（/ws/realtime）
- [x] 实时数据API（总览/单点/层级）
- [x] 历史数据查询API（聚合/导出/统计）
- [x] 告警引擎（阈值/升级/抑制/声光推送）
- [x] 告警管理API（列表/确认/解除/配置/统计）
- [x] 报表API（日报/月报/自定义/Excel导出）
- [x] 系统管理API（配置/健康检查/日志/备份）
- [x] 定时任务调度器（心跳检测/告警升级/备份/清理）

### 前端

- [x] 登录页
- [x] 主布局（侧边栏 + 顶部栏）
- [x] 数据总览（Dashboard）
- [x] 实时监控（卡片式数据展示）
- [x] 数据大屏投放模式（深色主题）
- [x] 数据点详情（实时值 + ECharts趋势图 + 告警记录）
- [x] 历史数据查询（图表 + 表格 + Excel导出）
- [x] 告警中心（实时告警 + 记录 + 配置 + 声光报警）
- [x] 报表中心（日报/月报/自定义）
- [x] 层级管理（树形CRUD）
- [x] 设备管理
- [x] 数据点管理
- [x] 协议管理（含测试功能）
- [x] 用户管理
- [x] 系统配置
- [x] 操作日志

## API接口

启动后访问 http://localhost:8000/api/docs 查看 Swagger UI 自动生成的API文档。

### 接口分组

| 模块 | 路径前缀 | 说明 |
|------|----------|------|
| 认证 | /api/v1/auth | 登录/登出/刷新/密码修改 |
| 层级 | /api/v1/hierarchy | 树形层级CRUD |
| 设备 | /api/v1/devices | 设备CRUD + 导入导出 |
| 数据点 | /api/v1/points | 数据点和数据项CRUD |
| 协议 | /api/v1/protocols | 协议模板管理 + 测试解析 |
| 实时 | /api/v1/realtime | 实时数据查询 |
| 历史 | /api/v1/history | 历史数据查询 + 导出 |
| 告警 | /api/v1/alarms | 告警管理 + 配置 |
| 报表 | /api/v1/reports | 日报/月报/自定义报表 |
| 用户 | /api/v1/users | 用户管理 |
| 系统 | /api/v1/system | 系统配置/健康检查/日志 |
| WebSocket | /ws/realtime | 实时数据推送 |

## 环境变量

参见 `.env.example`，主要配置项：

| 配置 | 说明 | 默认值 |
|------|------|--------|
| POSTGRES_* | PostgreSQL连接 | iot_db / postgres |
| TDENGINE_* | TDengine连接 | iot_data |
| JWT_SECRET_KEY | JWT密钥 | 需修改 |
| MQTT_BROKER_* | MQTT Broker连接 | emqx:1883 |
| TCP_* | TCP服务器监听 | 0.0.0.0:9000 |
