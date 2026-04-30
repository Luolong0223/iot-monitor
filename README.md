# 工业数据采集管理平台 (IoT-Monitor)

基于 FastAPI + TDengine + PostgreSQL + EMQX 的工业气体监测物联网平台，支持多种协议解析、实时数据采集、告警管理、报表生成等功能。

---

## 目录

- [系统架构](#系统架构)
- [技术栈](#技术栈)
- [功能模块](#功能模块)
- [项目结构](#项目结构)
- [部署指南](#部署指南)
  - [环境要求](#环境要求)
  - [一键部署](#一键部署)
  - [手动部署](#手动部署)
  - [前端部署](#前端部署)
  - [HTTPS 配置](#https-配置)
- [配置说明](#配置说明)
- [API 文档](#api-文档)
- [数据库初始化](#数据库初始化)
- [运维手册](#运维手册)
- [常见问题](#常见问题)

---

## 系统架构

```
┌─────────────┐      ┌─────────────┐      ┌──────────────────────────────┐
│   DTU 设备   │─────▶│  TCP :9000  │─────▶│                              │
│  (4G DTU)   │      │  (异步服务)  │      │      FastAPI Backend         │
└─────────────┘      └─────────────┘      │      ├─ 协议解析引擎          │
                                           │      ├─ 数据校验引擎          │
┌─────────────┐      ┌─────────────┐      │      ├─ 告警引擎              │
│  智能网关    │─────▶│ MQTT :1883  │─────▶│      ├─ WebSocket 实时推送    │
│  (EMQX)    │      │  (消息队列)  │      │      └─ APScheduler 定时任务  │
└─────────────┘      └─────────────┘      │                              │
                                           └──────┬───────┬───────┬───────┘
                                                  │       │       │
                              ┌─────────────────────┘       │       │
                              ▼                             ▼       ▼
                   ┌──────────────────┐          ┌─────────┐  ┌─────────┐
                   │  TDengine 3.x    │          │PostgreSQL│  │  Redis  │
                   │  (时序数据存储)    │          │ (业务数据)│  │ (缓存)  │
                   └──────────────────┘          └─────────┘  └─────────┘

┌─────────────┐      ┌─────────────┐
│   前端页面   │◀────▶│  Nginx :80  │──── 反向代理 ────▶ Backend :8000
│  (Vue 3)    │      │  (HTTPS:443)│──── WebSocket  ──▶ /ws/realtime
└─────────────┘      └─────────────┘
```

### 数据流转

```
设备上报 → MQTT/TCP 接收 → 协议解析 → 数据校验 → TDengine 存储
                                              ↓
                                         告警引擎检查 → WebSocket 推送前端
                                              ↓
                                         告警记录入库 → 升级/抑制/自动解除
```

---

## 技术栈

| 组件 | 技术 | 版本 | 用途 |
|------|------|------|------|
| Web 框架 | FastAPI | 0.115+ | REST API、WebSocket |
| 运行时 | Python | 3.11+ | 后端服务 |
| 业务数据库 | PostgreSQL | 16+ | 用户、设备、配置等结构化数据 |
| 时序数据库 | TDengine | 3.x | 传感器时序数据存储与聚合查询 |
| 缓存 | Redis | 7.x | 会话缓存、数据缓存 |
| MQTT Broker | EMQX | 5.x | 设备消息通信 |
| 任务调度 | APScheduler | 3.10+ | 心跳检查、告警升级、定时备份 |
| 认证 | JWT | HS256 | 用户认证与鉴权 |
| ORM | SQLAlchemy | 2.0+ | 异步数据库操作 |
| 反向代理 | Nginx | - | HTTP/HTTPS/WSS 代理 |

---

## 功能模块

### 1. 设备管理
- 设备 CRUD（编码、名称、类型、SIM卡、安装日期等）
- 设备状态查询（在线/离线/维护）
- 心跳监控（自动检测离线）
- Excel 批量导入/导出

### 2. 数据点管理
- 数据点 CRUD（编码、名称、位置、经纬度）
- 数据项 CRUD（编码、单位、量程、换算系数、告警阈值）
- 支持一个数据点下挂载多个数据项
- Excel 批量导入

### 3. 协议管理
- 协议模板 CRUD
- 支持 6 种协议类型：
  - `fixed_offset` — 固定偏移量解析
  - `modbus_rtu` — Modbus RTU
  - `modbus_tcp` — Modbus TCP
  - `custom_frame` — 自定义帧格式（支持帧头/CRC校验）
  - `json` — JSON 格式
  - `csv` — CSV 格式
- 在线测试解析（输入协议配置+十六进制报文→返回解析结果）
- JSON 导入/导出

### 4. 协议解析引擎
- CRC16/CRC32 校验验证
- 大端/小端字节序支持
- 数据换算: `value × scale + offset`
- 支持 int8/uint8/int16/uint16/int32/uint32/float32/float64

### 5. 数据校验引擎
- 范围检查（量程上下限）
- 突变检测（滑动窗口 + 标准差）
- 连续零值检测
- 连续重复值检测
- 空值/空字符串检测
- 时间戳有效性校验
- 每项独立配置开关

### 6. 实时数据
- 仪表盘概览（设备/数据点/告警统计）
- 单数据点实时查询
- 层级子树实时数据查询
- WebSocket 实时推送

### 7. 历史数据
- 时间范围查询
- 聚合查询（avg/max/min/sum/count）
- 自定义聚合间隔（1m/5m/1h/1d）
- 统计端点（平均/最大/最小/首值/末值）
- Excel 导出

### 8. 告警管理
- 阈值告警（上限/下限）
- 数据质量告警（突变/零值/重复）
- 设备离线告警
- 告警抑制（同类型同数据项 5 分钟内不重复）
- 告警升级（warning→critical 分级升级）
- 自动解除（设备上线自动解除离线告警）
- 告警确认/解除
- 告警统计（按状态/级别/类型）
- 告警通知配置

### 9. 报表管理
- 日报表
- 月报表
- 自定义时间范围报表
- Excel 导出（概览+数据统计+告警明细）

### 10. 系统管理
- 系统配置 CRUD（分组管理）
- 健康检查（数据库/TDengine/MQTT/TCP 状态）
- 操作日志查询
- 手动数据库备份
- 系统统计

### 11. 定时任务
- 心跳检查（每 30 秒）
- 告警升级检查（每 5 分钟）
- 每日自动备份（默认 02:00）
- 操作日志清理（保留 90 天）

---

## 项目结构

```
iot-monitor/
├── deploy.sh                     # 一键部署脚本
├── README.md                     # 项目说明文档
│
├── backend/
│   ├── requirements.txt          # Python 依赖
│   ├── init_db.py                # 数据库初始化脚本
│   │
│   └── app/
│       ├── main.py               # FastAPI 应用入口
│       ├── config.py             # 配置管理（环境变量/.env）
│       ├── database.py           # 数据库连接管理
│       ├── schemas.py            # Pydantic 请求/响应模型
│       │
│       ├── api/
│       │   └── v1/
│       │       ├── __init__.py   # 路由注册
│       │       ├── auth.py       # 认证模块（登录/登出/Token刷新）
│       │       ├── hierarchy.py  # 层级管理
│       │       ├── users.py      # 用户管理
│       │       ├── devices.py    # 设备管理
│       │       ├── data_points.py# 数据点管理
│       │       ├── protocols.py  # 协议管理
│       │       ├── realtime.py   # 实时数据
│       │       ├── history.py    # 历史数据
│       │       ├── alarms.py     # 告警管理
│       │       ├── reports.py    # 报表管理
│       │       ├── system.py     # 系统管理
│       │       └── websocket.py  # WebSocket 实时推送
│       │
│       ├── core/
│       │   └── security.py       # JWT 生成/验证、密码加密
│       │
│       ├── models/
│       │   ├── __init__.py       # 模型导出
│       │   ├── hierarchy.py      # 层级模型
│       │   ├── device.py         # 设备模型
│       │   ├── data_point.py     # 数据点/数据项模型
│       │   ├── protocol.py       # 协议模板模型
│       │   ├── user.py           # 用户模型
│       │   ├── alarm.py          # 告警记录/通知模型
│       │   └── system.py         # 系统配置/操作日志模型
│       │
│       ├── services/
│       │   ├── protocol_parser.py # 协议解析引擎
│       │   ├── data_validator.py  # 数据校验引擎
│       │   ├── tdengine_service.py# TDengine 服务
│       │   ├── alarm_engine.py    # 告警引擎
│       │   ├── scheduler.py       # 定时任务调度
│       │   ├── mqtt_handler.py    # MQTT 消息处理
│       │   └── tcp_handler.py     # TCP 数据处理
│       │
│       ├── mqtt/
│       │   └── client.py         # MQTT 客户端
│       │
│       └── tcp/
│           └── server.py         # TCP 异步服务器
│
└── frontend/                     # 前端项目（Vue 3）
```

---

## 部署指南

### 环境要求

| 组件 | 最低配置 | 推荐配置 |
|------|---------|---------|
| 操作系统 | CentOS Stream 10 | CentOS Stream 10 / Rocky Linux 9 |
| CPU | 2 核 | 4 核+ |
| 内存 | 4 GB | 8 GB+ |
| 磁盘 | 40 GB | 100 GB+ (SSD) |
| Python | 3.11 | 3.11+ |
| PostgreSQL | 15 | 16+ |
| TDengine | 3.0 | 3.3+ |

### 一键部署

```bash
# 1. 克隆项目
git clone https://github.com/Luolong0223/iot-monitor.git
cd iot-monitor

# 2. 执行一键部署
sudo bash deploy.sh
```

**自定义配置部署：**

```bash
# 自定义数据库密码、管理员密码、域名
sudo DB_PASS=MyDBPass123 \
     ADMIN_PASS=MyAdminPass456 \
     DOMAIN=iot.example.com \
     MQTT_USER=my_mqtt_user \
     MQTT_PASS=MyMQTTPass789 \
     bash deploy.sh
```

部署完成后终端会输出所有账号密码信息，请妥善保存。

### 手动部署

#### 第一步：系统基础环境

```bash
# 更新系统
sudo dnf update -y

# 安装基础工具
sudo dnf install -y wget curl git vim tar gcc gcc-c++ make epel-release

# 配置防火墙
sudo firewall-cmd --permanent --add-port=80/tcp
sudo firewall-cmd --permanent --add-port=443/tcp
sudo firewall-cmd --permanent --add-port=1883/tcp
sudo firewall-cmd --permanent --add-port=9000/tcp
sudo firewall-cmd --permanent --add-port=6030/tcp
sudo firewall-cmd --permanent --add-port=5432/tcp
sudo firewall-cmd --reload
```

#### 第二步：安装 PostgreSQL

```bash
# 安装
sudo dnf install -y postgresql-server postgresql

# 初始化
sudo postgresql-setup --initdb

# 启动
sudo systemctl enable --now postgresql

# 创建用户和数据库
sudo -u postgres psql <<EOF
CREATE USER iot_user WITH PASSWORD 'your_secure_password';
CREATE DATABASE iot_db OWNER iot_user;
GRANT ALL PRIVILEGES ON DATABASE iot_db TO iot_user;
EOF

# 修改认证方式 (ident → md5)
sudo sed -i 's/ident/md5/g' /var/lib/pgsql/data/pg_hba.conf
sudo systemctl restart postgresql

# 验证
psql -U iot_user -d iot_db -c "SELECT 1;"
```

#### 第三步：安装 TDengine

```bash
# 下载
wget https://www.taosdata.com/assets-download/3.0/TDengine-server-3.3.4.3-x86_64.rpm

# 安装
sudo rpm -ivh TDengine-server-3.3.4.3-x86_64.rpm

# 启动
sudo systemctl enable --now taosd
sudo systemctl enable --now taosadapter

# 验证
taos -s "SHOW DATABASES;"
```

#### 第四步：安装 Redis

```bash
sudo dnf install -y redis
sudo systemctl enable --now redis

# 验证
redis-cli ping
# 返回: PONG
```

#### 第五步：安装 EMQX (MQTT Broker)

```bash
# 添加仓库
cat > /etc/yum.repos.d/emqx.repo <<'REPO'
[emqx]
name=emqx
baseurl=https://repos.emqx.io/emqx-ce/rpm/el/9/$basearch
enabled=1
gpgcheck=0
REPO

# 安装
sudo dnf install -y emqx

# 启动
sudo systemctl enable --now emqx

# 验证
curl -s http://localhost:18083/api/v5/status
# Web 管理: http://your-ip:18083 (默认 admin/public)
```

#### 第六步：安装 Python

```bash
sudo dnf install -y python3.11 python3.11-devel python3-pip

# 如果没有 3.11，使用系统自带的 python3
python3 --version
```

#### 第七步：部署后端应用

```bash
# 克隆代码
cd /opt
git clone https://github.com/Luolong0223/iot-monitor.git
cd iot-monitor/backend

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install --upgrade pip
pip install -r requirements.txt
```

#### 第八步：创建配置文件

```bash
cat > /opt/iot-monitor/backend/.env <<'EOF'
# ========== PostgreSQL ==========
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=iot_db
POSTGRES_USER=iot_user
POSTGRES_PASSWORD=your_secure_password

# ========== TDengine ==========
TDENGINE_HOST=localhost
TDENGINE_PORT=6030
TDENGINE_DB=iot_data
TDENGINE_KEEP_DAYS=365

# ========== Redis ==========
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# ========== JWT ==========
JWT_SECRET_KEY=替换为随机密钥(运行 openssl rand -hex 32 生成)
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=120
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# ========== MQTT ==========
MQTT_BROKER_HOST=localhost
MQTT_BROKER_PORT=1883
MQTT_USERNAME=iot_server
MQTT_PASSWORD=your_mqtt_password

# ========== TCP Server ==========
TCP_HOST=0.0.0.0
TCP_PORT=9000

# ========== 系统 ==========
SYSTEM_NAME=工业数据采集管理平台
LOG_LEVEL=info
DEBUG=false

# ========== CORS ==========
CORS_ORIGINS=["http://localhost","http://your-domain.com"]

# ========== 备份 ==========
BACKUP_ENABLED=true
BACKUP_TIME=02:00
BACKUP_RETAIN_DAYS=30
BACKUP_PATH=/data/backup
EOF

# 设置权限
chmod 600 /opt/iot-monitor/backend/.env

# 创建备份目录
sudo mkdir -p /data/backup
sudo chown $(whoami):$(whoami) /data/backup
```

#### 第九步：初始化数据库

```bash
cd /opt/iot-monitor/backend
source venv/bin/activate

python init_db.py
```

初始化脚本会自动完成：
- 创建所有数据库表（PostgreSQL）
- 创建 TDengine 超级表
- 初始化系统配置项
- 创建默认超级管理员（admin / Admin@123456）
- 创建内置协议模板（Modbus RTU、自定义帧、JSON）

#### 第十步：测试启动

```bash
cd /opt/iot-monitor/backend
source venv/bin/activate

# 直接启动测试
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# 访问 API 文档: http://your-ip:8000/api/docs
# 访问健康检查: http://your-ip:8000/health
```

#### 第十一步：配置 Systemd 服务

```bash
sudo cat > /etc/systemd/system/iot-monitor.service <<EOF
[Unit]
Description=IoT Monitor Backend
After=network.target postgresql.service taosd.service redis.service emqx.service
Wants=postgresql.service taosd.service redis.service emqx.service

[Service]
Type=exec
User=root
WorkingDirectory=/opt/iot-monitor/backend
Environment="PATH=/opt/iot-monitor/backend/venv/bin"
EnvironmentFile=/opt/iot-monitor/backend/.env
ExecStart=/opt/iot-monitor/backend/venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=5
LimitNOFILE=65535

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now iot-monitor

# 查看状态
sudo systemctl status iot-monitor
```

#### 第十二步：配置 Nginx

```bash
sudo dnf install -y nginx

sudo cat > /etc/nginx/conf.d/iot-monitor.conf <<'EOF'
server {
    listen 80;
    server_name your-domain.com;

    client_max_body_size 50m;

    # API 代理
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300;
        proxy_connect_timeout 60;
    }

    # WebSocket 代理
    location /ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
    }

    # 静态资源缓存
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf)$ {
        proxy_pass http://127.0.0.1:8000;
        expires 7d;
        add_header Cache-Control "public, immutable";
    }
}
EOF

sudo nginx -t
sudo systemctl enable --now nginx
```

### 前端部署

```bash
# 安装 Node.js 20
curl -fsSL https://rpm.nodesource.com/setup_20.x | sudo bash -
sudo dnf install -y nodejs

# 进入前端目录
cd /opt/iot-monitor/frontend

# 安装依赖
npm install

# 修改 API 地址
# 编辑 .env.production 文件
echo "VITE_API_BASE_URL=http://your-domain.com" > .env.production

# 构建
npm run build

# 复制到 Nginx 静态目录
sudo cp -r dist/* /usr/share/nginx/html/

# 或配置 Nginx 直接代理前端 dev server（开发模式）
# npm run dev
```

### HTTPS 配置

```bash
# 安装 certbot
sudo dnf install -y certbot python3-certbot-nginx

# 申请证书
sudo certbot --nginx -d your-domain.com

# 自动续期
sudo certbot renew --dry-run
```

或手动配置：

```bash
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    # ... 同上 location 配置 ...
}

server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$host$request_uri;
}
```

---

## 配说说明

### 环境变量 (.env)

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `POSTGRES_HOST` | localhost | PostgreSQL 地址 |
| `POSTGRES_PORT` | 5432 | PostgreSQL 端口 |
| `POSTGRES_DB` | iot_db | 数据库名 |
| `POSTGRES_USER` | iot_user | 数据库用户 |
| `POSTGRES_PASSWORD` | - | 数据库密码 |
| `TDENGINE_HOST` | localhost | TDengine 地址 |
| `TDENGINE_PORT` | 6030 | TDengine 端口 |
| `TDENGINE_DB` | iot_data | TDengine 数据库名 |
| `TDENGINE_KEEP_DAYS` | 365 | 数据保留天数 |
| `REDIS_HOST` | localhost | Redis 地址 |
| `REDIS_PORT` | 6379 | Redis 端口 |
| `JWT_SECRET_KEY` | - | JWT 签名密钥 |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | 120 | Token 有效期(分钟) |
| `MQTT_BROKER_HOST` | localhost | EMQX 地址 |
| `MQTT_BROKER_PORT` | 1883 | MQTT 端口 |
| `MQTT_USERNAME` | - | MQTT 用户名 |
| `MQTT_PASSWORD` | - | MQTT 密码 |
| `TCP_HOST` | 0.0.0.0 | TCP 监听地址 |
| `TCP_PORT` | 9000 | TCP 监听端口 |
| `LOG_LEVEL` | info | 日志级别 |
| `BACKUP_ENABLED` | true | 是否自动备份 |
| `BACKUP_TIME` | 02:00 | 备份时间 |
| `BACKUP_RETAIN_DAYS` | 30 | 备份保留天数 |
| `BACKUP_PATH` | /data/backup | 备份目录 |

### 系统配置 (数据库)

系统运行后可通过 API `/api/v1/system/config` 管理以下配置：

| 配置键 | 默认值 | 说明 |
|--------|--------|------|
| `alarm.suppression_minutes` | 5 | 告警抑制时间(分钟) |
| `alarm.escalation_warning` | 15,30,60 | warning 升级阈值 |
| `alarm.escalation_critical` | 10,20,40 | critical 升级阈值 |
| `heartbeat.timeout_minutes` | 3 | 心跳超时时间 |
| `data.cleanup_days` | 90 | 日志保留天数 |

---

## API 文档

启动后访问 Swagger UI: `http://your-ip/api/docs`

### API 模块一览

| 模块 | 路径前缀 | 认证 | 说明 |
|------|----------|------|------|
| 认证 | `/api/v1/auth` | 无(登录) | 登录/登出/Token刷新/修改密码 |
| 层级管理 | `/api/v1/hierarchy` | 需要 | 树形层级 CRUD |
| 用户管理 | `/api/v1/users` | 管理员 | 用户 CRUD/重置密码 |
| 设备管理 | `/api/v1/devices` | 需要 | 设备 CRUD/状态/导入导出 |
| 数据点管理 | `/api/v1/data-points` | 需要 | 数据点+数据项 CRUD |
| 协议管理 | `/api/v1/protocols` | 需要 | 协议模板 CRUD/测试解析 |
| 实时数据 | `/api/v1/realtime` | 需要 | 仪表盘/实时查询 |
| 历史数据 | `/api/v1/history` | 需要 | 聚合查询/统计/导出 |
| 告警管理 | `/api/v1/alarms` | 需要 | 告警 CRUD/配置/统计 |
| 报表 | `/api/v1/reports` | 需要 | 日报/月报/自定义报表 |
| 系统管理 | `/api/v1/system` | 管理员 | 配置/健康检查/日志/备份 |
| WebSocket | `/ws/realtime` | Token | 实时数据推送 |

### 认证方式

所有需要认证的接口使用 Bearer Token：

```
Authorization: Bearer <access_token>
```

### 统一响应格式

```json
{
    "code": 200,
    "message": "success",
    "data": { ... }
}
```

### WebSocket 连接

```javascript
// 连接
const ws = new WebSocket('ws://your-ip/ws/realtime?token=YOUR_JWT_TOKEN');

// 订阅数据点
ws.send(JSON.stringify({ action: "subscribe", point_ids: [1, 2, 3] }));

// 接收数据
ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    // msg.type: "data_update" | "alarm" | "pong"
};

// 心跳保活
setInterval(() => ws.send(JSON.stringify({ action: "ping" })), 30000);
```

---

## 数据库初始化

`init_db.py` 脚本执行以下操作：

1. **创建数据库表** — 根据 SQLAlchemy 模型自动创建所有 PostgreSQL 表
2. **创建 TDengine 超级表** — `sensor_data` 超级表
3. **初始化系统配置** — 告警、心跳、备份等默认配置
4. **创建默认管理员** — `admin / Admin@123456`
5. **创建内置协议模板** — Modbus RTU、自定义帧、JSON 三种模板

```bash
cd /opt/iot-monitor/backend
source venv/bin/activate
python init_db.py
```

重新初始化（不会覆盖已有数据）：

```bash
python init_db.py
# 已存在的用户、配置、协议模板会跳过
```

---

## 运维手册

### 常用命令

```bash
# 服务管理
systemctl start iot-monitor      # 启动
systemctl stop iot-monitor       # 停止
systemctl restart iot-monitor    # 重启
systemctl status iot-monitor     # 状态

# 查看日志
journalctl -u iot-monitor -f                    # 实时日志
journalctl -u iot-monitor --since "1 hour ago"  # 最近1小时
journalctl -u iot-monitor -n 200                # 最近200条

# 其他服务
systemctl status postgresql taosd redis emqx nginx
```

### 数据库备份

```bash
# 自动备份（每天 02:00 由调度器执行）
# 备份文件存放在 /data/backup/

# 手动备份
pg_dump -U iot_user -d iot_db > /data/backup/manual_$(date +%Y%m%d_%H%M%S).sql

# 恢复
psql -U iot_user -d iot_db < /data/backup/backup_file.sql

# 通过 API 触发备份（需要 superadmin）
curl -X POST http://localhost:8000/api/v1/system/backup \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 日志清理

操作日志自动清理保留 90 天，可通过 API 修改配置：

```bash
curl -X PUT http://localhost:8000/api/v1/system/config/data.cleanup_days \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"config_value": "60"}'
```

### 监控检查

```bash
# 健康检查
curl http://localhost/health
curl http://localhost/api/v1/system/health

# 服务连通性
psql -U iot_user -d iot_db -c "SELECT 1;"    # PostgreSQL
taos -s "SHOW DATABASES;"                      # TDengine
redis-cli ping                                  # Redis
curl http://localhost:18083/api/v5/status       # EMQX
```

### 性能调优

**PostgreSQL:**
```bash
# /var/lib/pgsql/data/postgresql.conf
shared_buffers = 256MB
effective_cache_size = 768MB
work_mem = 16MB
max_connections = 200
```

**TDengine:**
```sql
-- 建库时调整参数
CREATE DATABASE iot_data KEEP 365 DURATION 30 BUFFER 64 WAL_LEVEL 1;
```

**Nginx:**
```nginx
worker_processes auto;
worker_connections 4096;
```

---

## 常见问题

### Q: 启动报错 "connection refused"

检查对应服务是否启动：
```bash
systemctl status postgresql taosd redis emqx
```

### Q: MQTT 连接不上

1. 检查 EMQX 状态: `systemctl status emqx`
2. 检查端口: `ss -tlnp | grep 1883`
3. 检查防火墙: `firewall-cmd --list-ports`
4. 检查 .env 中的 MQTT 配置

### Q: TDengine 写入失败

1. 确认 taosd 运行: `systemctl status taosd`
2. 确认数据库存在: `taos -s "SHOW DATABASES;"`
3. 检查端口: `ss -tlnp | grep 6030`

### Q: 忘记管理员密码

```bash
cd /opt/iot-monitor/backend
source venv/bin/activate
python -c "
import asyncio
from app.database import async_session
from app.models.user import User
from app.core.security import hash_password
from sqlalchemy import select

async def reset():
    async with async_session() as db:
        result = await db.execute(select(User).where(User.username == 'admin'))
        user = result.scalar_one_or_none()
        if user:
            user.password_hash = hash_password('Admin@123456')
            user.login_attempts = 0
            user.locked_until = None
            await db.commit()
            print('密码已重置为: Admin@123456')

asyncio.run(reset())
"
```

### Q: WebSocket 连接失败

1. 检查 Nginx WebSocket 代理配置
2. 确认 Token 有效
3. 检查浏览器控制台错误信息

### Q: 如何修改 MQTT 主题格式

编辑 `backend/app/mqtt/client.py` 中的 `topics` 列表：

```python
topics = [
    ("your/custom/topic/+/data", 0),
    ("your/custom/topic/+/heartbeat", 0),
]
```

### Q: 如何添加新的协议类型

在 `backend/app/services/protocol_parser.py` 中：

1. 在 `dispatch` 字典中添加新类型
2. 实现对应的 `_parse_xxx` 方法
3. 在 `ProtocolParser` 类中添加方法

---

## 许可证

Private - Internal Use Only

---

## 联系方式

- 项目地址: https://github.com/Luolong0223/iot-monitor
- 问题反馈: GitHub Issues
