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
cd gas-monitor

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
gas-monitor/
├── docker-compose.yml          # Docker编排
├── .env.example                # 环境变量模板
├── nginx/nginx.conf            # Nginx配置
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py             # FastAPI入口
│       ├── config.py           # 配置管理
│       ├── database.py         # 数据库连接
│       ├── schemas.py          # 数据模型
│       ├── models/             # ORM模型
│       ├── api/v1/             # API路由
│       ├── core/               # 核心模块(认证等)
│       ├── services/           # 业务逻辑
│       ├── mqtt/               # MQTT客户端
│       ├── tcp/                # TCP服务
│       └── utils/              # 工具函数
├── frontend/                   # Vue3前端
├── scripts/                    # 初始化脚本
├── docs/                       # 文档
└── backup/                     # 备份目录
```

## 开发进度

- [x] 项目骨架搭建
- [x] 数据库模型设计
- [x] 用户认证（JWT）
- [x] 层级管理API
- [x] 用户管理API
- [ ] 设备管理API
- [ ] 数据点管理API
- [ ] 协议管理API
- [ ] MQTT数据接收
- [ ] TCP数据接收
- [ ] 实时数据推送（WebSocket）
- [ ] 历史数据查询
- [ ] 告警系统
- [ ] 报表系统
- [ ] 前端开发
- [ ] 部署与测试

## API文档

启动后访问 http://localhost:8000/api/docs 查看 Swagger UI 自动生成的API文档。
