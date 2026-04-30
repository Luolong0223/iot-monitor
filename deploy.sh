#!/bin/bash
# ============================================================
#  IoT-Monitor 一键部署脚本 (CentOS Stream 10)
#
#  使用: sudo -E DB_PASS=xxx ADMIN_PASS=xxx bash deploy.sh
#
#  功能:
#    1. 安装系统依赖 + Docker
#    2. 安装并配置 PostgreSQL (dnf)
#    3. 安装并配置 TDengine (Docker)
#    4. 安装并配置 Redis (Docker)
#    5. 安装并配置 EMQX (Docker)
#    6. 部署后端应用
#    7. 配置 Systemd 服务
#    8. 配置 Nginx 反向代理
#    9. 初始化数据库
# ============================================================

set -e

# ============ 颜色输出 ============
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${BLUE}[INFO]${NC} $1"; }
ok()    { echo -e "${GREEN}[OK]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
fail()  { echo -e "${RED}[FAIL]${NC} $1"; exit 1; }

# ============ 配置变量 ============
APP_DIR="/opt/iot-monitor"
DB_NAME="iot_db"
DB_USER="iot_user"
DB_PASS="${DB_PASS:-IoT@$(openssl rand -hex 8)}"
TDENGINE_DB="iot_data"
JWT_SECRET=$(openssl rand -hex 32)
MQTT_USER="${MQTT_USER:-iot_server}"
MQTT_PASS="${MQTT_PASS:-MQTT@$(openssl rand -hex 8)}"
DOMAIN="${DOMAIN:-localhost}"
ADMIN_PASS="${ADMIN_PASS:-Admin@123456}"

# ============ 前置检查 ============
check_root() {
    if [[ $EUID -ne 0 ]]; then
        fail "请使用 root 权限运行: sudo bash deploy.sh"
    fi
}

check_os() {
    if ! grep -q "CentOS" /etc/os-release 2>/dev/null; then
        warn "当前系统非 CentOS，脚本可能不完全兼容"
    fi
    ok "系统检查通过"
}

# ============ 容器运行时（兼容 Docker/Podman） ============
# CentOS Stream 10 自带 podman，docker 命令是 podman 的别名
# 统一使用 podman 命令，语法与 docker 完全兼容
CONTAINER_CMD="podman"

# ============ 1. 系统基础 ============
setup_system() {
    info "配置系统基础环境..."

    dnf update -y -q 2>/dev/null || true
    dnf install -y -q wget curl git vim tar gcc gcc-c++ make \
        epel-release yum-utils policycoreutils-python-utils 2>/dev/null || true

    # 确保 podman 可用
    if ! command -v podman &>/dev/null; then
        dnf install -y -q podman
    fi
    ok "容器运行时: $(${CONTAINER_CMD} --version)"

    # 配置 podman（兼容 systemd 容器自动重启）
    touch /etc/containers/nodocker 2>/dev/null || true
    systemctl enable --now podman.socket 2>/dev/null || true
    systemctl enable --now podman-restart 2>/dev/null || true

    # 防火墙
    if systemctl is-active --quiet firewalld; then
        firewall-cmd --permanent --add-port=80/tcp 2>/dev/null || true
        firewall-cmd --permanent --add-port=443/tcp 2>/dev/null || true
        firewall-cmd --permanent --add-port=1883/tcp 2>/dev/null || true
        firewall-cmd --permanent --add-port=8883/tcp 2>/dev/null || true
        firewall-cmd --permanent --add-port=9000/tcp 2>/dev/null || true
        firewall-cmd --permanent --add-port=6030/tcp 2>/dev/null || true
        firewall-cmd --permanent --add-port=5432/tcp 2>/dev/null || true
        firewall-cmd --reload 2>/dev/null || true
        ok "防火墙端口已开放"
    else
        warn "firewalld 未运行，跳过防火墙配置"
    fi

    # SELinux
    if command -v getenforce &>/dev/null && [ "$(getenforce)" = "Enforcing" ]; then
        setenforce 0
        sed -i 's/SELINUX=enforcing/SELINUX=permissive/' /etc/selinux/config
        warn "SELinux 已设为 permissive"
    fi

    ok "系统基础环境配置完成"
}

# ============ 2. PostgreSQL ============
setup_postgresql() {
    info "安装 PostgreSQL..."

    dnf install -y -q postgresql-server postgresql

    if [ ! -f /var/lib/pgsql/data/PG_VERSION ]; then
        postgresql-setup --initdb
    fi

    systemctl enable --now postgresql

    # 创建用户和数据库
    sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='${DB_USER}'" | grep -q 1 || \
        sudo -u postgres psql -c "CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASS}';"

    sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" | grep -q 1 || \
        sudo -u postgres psql -c "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};"

    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};"

    # 修改认证方式
    PG_HBA="/var/lib/pgsql/data/pg_hba.conf"
    if grep -q "ident" "$PG_HBA"; then
        sed -i 's/ident/md5/g' "$PG_HBA"
        systemctl restart postgresql
    fi

    ok "PostgreSQL 安装完成 (密码: ${DB_PASS})"
}

# ============ 3. TDengine (Docker) ============
setup_tdengine() {
    info "安装 TDengine (Docker)..."

    # 启动 TDengine 容器
    ${CONTAINER_CMD} rm -f tdengine 2>/dev/null || true
    ${CONTAINER_CMD} run -d --name tdengine --restart=always \
        -p 6030:6030 -p 6041:6041 \
        -v tdengine_data:/var/lib/taos \
        docker.io/tdengine/tdengine:3

    # 等待 TDengine 就绪
    info "等待 TDengine 启动..."
    sleep 8

    # 创建数据库
    ${CONTAINER_CMD} exec tdengine taos -s "CREATE DATABASE IF NOT EXISTS ${TDENGINE_DB} KEEP 365 DURATION 30 BUFFER 16 WAL_LEVEL 1 PRECISION 'ms';" || \
        warn "TDengine 数据库创建失败，稍后由应用自动创建"

    ok "TDengine 安装完成 (Docker)"
}

# ============ 4. Redis (Docker) ============
setup_redis() {
    info "安装 Redis (Docker)..."

    ${CONTAINER_CMD} rm -f redis 2>/dev/null || true
    ${CONTAINER_CMD} run -d --name redis --restart=always \
        -p 6379:6379 \
        -v redis_data:/data \
        docker.io/redis:7-alpine

    sleep 3
    ${CONTAINER_CMD} exec redis redis-cli ping | grep -q PONG || warn "Redis 启动异常"

    ok "Redis 安装完成 (Docker)"
}

# ============ 5. EMQX (Docker) ============
setup_emqx() {
    info "安装 EMQX (Docker)..."

    ${CONTAINER_CMD} rm -f emqx 2>/dev/null || true
    ${CONTAINER_CMD} run -d --name emqx --restart=always \
        -p 1883:1883 -p 8083:8083 -p 8883:8883 -p 18083:18083 \
        -v emqx_data:/opt/emqx/data \
        docker.io/emqx/emqx:5

    # 等待 EMQX 启动
    info "等待 EMQX 启动..."
    sleep 10

    # 通过 REST API 创建 MQTT 用户 (EMQX 5.x)
    if curl -s http://localhost:18083/api/v5/status >/dev/null 2>&1; then
        # 添加认证方式（密码内置数据库）
        curl -s -X POST "http://localhost:18083/api/v5/authentication" \
            -u "admin:public" \
            -H "Content-Type: application/json" \
            -d '{"mechanism":"password_based","backend":"built_in_database","password_hash_algorithm":{"name":"sha256","salt_position":"suffix"}}' 2>/dev/null || true
        sleep 2
        # 创建 MQTT 用户
        curl -s -X POST "http://localhost:18083/api/v5/authentication/password_based:built_in_database/users" \
            -u "admin:public" \
            -H "Content-Type: application/json" \
            -d "{\"user_id\":\"${MQTT_USER}\",\"password\":\"${MQTT_PASS}\"}" 2>/dev/null || true
        # 修改 admin 默认密码
        curl -s -X PUT "http://localhost:18083/api/v5/users/admin" \
            -u "admin:public" \
            -H "Content-Type: application/json" \
            -d "{\"password\":\"${MQTT_PASS}\"}" 2>/dev/null || true
        ok "EMQX 安装完成 (MQTT用户: ${MQTT_USER})"
    else
        warn "EMQX 启动超时，请手动检查"
    fi
}

# ============ 6. Python 环境 ============
setup_python() {
    info "安装 Python 环境..."

    dnf install -y -q python3 python3-devel python3-pip 2>/dev/null

    PYTHON_CMD="python3"
    PY_VER=$(${PYTHON_CMD} --version 2>&1 | grep -oP '\d+\.\d+')
    info "检测到 Python 版本: ${PY_VER}"

    # 确保 venv 模块可用
    dnf install -y -q python3-virtualenv 2>/dev/null || \
        ${PYTHON_CMD} -m ensurepip 2>/dev/null || true

    ok "Python 安装完成 ($(${PYTHON_CMD} --version))"
}

# ============ 7. 部署应用 ============
deploy_app() {
    info "部署后端应用..."

    # 克隆代码
    if [ -d "${APP_DIR}" ]; then
        cd "${APP_DIR}"
        git pull origin master 2>/dev/null || true
    else
        git clone https://github.com/Luolong0223/iot-monitor.git "${APP_DIR}"
        cd "${APP_DIR}"
    fi

    cd backend

    # 创建虚拟环境
    ${PYTHON_CMD} -m venv venv
    source venv/bin/activate

    pip install --upgrade pip -q
    pip install -r requirements.txt -q

    # 创建 .env 文件
    cat > .env <<EOF
# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=${DB_NAME}
POSTGRES_USER=${DB_USER}
POSTGRES_PASSWORD=${DB_PASS}

# TDengine
TDENGINE_HOST=localhost
TDENGINE_PORT=6030
TDENGINE_DB=${TDENGINE_DB}

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# JWT
JWT_SECRET_KEY=${JWT_SECRET}
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=120
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# MQTT
MQTT_BROKER_HOST=localhost
MQTT_BROKER_PORT=1883
MQTT_USERNAME=${MQTT_USER}
MQTT_PASSWORD=${MQTT_PASS}

# TCP Server
TCP_HOST=0.0.0.0
TCP_PORT=9000

# 系统
SYSTEM_NAME=工业数据采集管理平台
LOG_LEVEL=info
DEBUG=false

# CORS
CORS_ORIGINS=["http://localhost","http://${DOMAIN}","https://${DOMAIN}"]

# 备份
BACKUP_ENABLED=true
BACKUP_TIME=02:00
BACKUP_RETAIN_DAYS=30
BACKUP_PATH=/data/backup
EOF

    chmod 600 .env

    # 创建必要目录
    mkdir -p /data/backup
    mkdir -p logs

    ok "应用部署完成"
}

# ============ 8. 初始化数据库 ============
init_database() {
    info "初始化数据库..."

    cd "${APP_DIR}/backend"
    source venv/bin/activate

    export ADMIN_PASS="${ADMIN_PASS}"
    python init_db.py

    ok "数据库初始化完成"
}

# ============ 9. Systemd 服务 ============
setup_systemd() {
    info "配置 Systemd 服务..."

    cat > /etc/systemd/system/iot-monitor.service <<EOF
[Unit]
Description=IoT Monitor Backend
After=network.target postgresql.service
    systemctl enable --now podman-restart 2>/dev/null || true
Wants=postgresql.service
    systemctl enable --now podman-restart 2>/dev/null || true

[Service]
Type=exec
User=root
WorkingDirectory=${APP_DIR}/backend
Environment="PATH=${APP_DIR}/backend/venv/bin"
EnvironmentFile=${APP_DIR}/backend/.env
ExecStart=${APP_DIR}/backend/venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=5
LimitNOFILE=65535

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable iot-monitor

    ok "Systemd 服务配置完成"
}

# ============ 10. Nginx ============
setup_nginx() {
    info "配置 Nginx..."

    dnf install -y -q nginx

    cat > /etc/nginx/conf.d/iot-monitor.conf <<EOF
server {
    listen 80;
    server_name ${DOMAIN};

    client_max_body_size 50m;

    # 前端静态资源
    location / {
        root /usr/share/nginx/html;
        index index.html;
        try_files \$uri \$uri/ /index.html;
    }

    # API 代理
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 300;
        proxy_connect_timeout 60;
    }

    # 登录接口限流
    limit_req_zone \$binary_remote_addr zone=login:10m rate=5r/m;
    location /api/v1/auth/login {
        limit_req zone=login burst=3 nodelay;
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }

    # WebSocket 代理
    location /ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_read_timeout 86400;
    }

    # 健康检查
    location /health {
        proxy_pass http://127.0.0.1:8000;
    }

    # 静态文件缓存
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf)$ {
        expires 7d;
        add_header Cache-Control "public, immutable";
    }
}
EOF

    nginx -t && systemctl enable --now nginx

    ok "Nginx 配置完成"
}

# ============ 启动所有服务 ============
start_services() {
    info "启动所有服务..."

    systemctl restart postgresql
    sleep 2
    systemctl start iot-monitor
    systemctl restart nginx

    # 确认 Docker 容器运行状态
    ${CONTAINER_CMD} start tdengine redis emqx 2>/dev/null || true

    ok "所有服务已启动"
}

# ============ 输出信息 ============
print_summary() {
    echo ""
    echo "============================================================"
    echo -e "  ${GREEN}✅ IoT-Monitor 部署完成!${NC}"
    echo "============================================================"
    echo ""
    echo "  📌 访问地址:"
    echo "     前端页面: http://${DOMAIN}"
    echo "     API 文档: http://${DOMAIN}/api/docs"
    echo "     健康检查: http://${DOMAIN}/health"
    echo ""
    echo "  🔐 默认管理员:"
    echo "     用户名: admin"
    echo "     密  码: ${ADMIN_PASS}"
    echo "     ⚠️  请登录后立即修改密码!"
    echo ""
    echo "  📊 服务信息:"
    echo "     PostgreSQL: localhost:5432 (${DB_NAME})"
    echo "     TDengine:   localhost:6030 (${TDENGINE_DB}) [Docker]"
    echo "     Redis:      localhost:6379 [Docker]"
    echo "     EMQX MQTT:  localhost:1883 [Docker]"
    echo "     EMQX 管理:  http://localhost:18083 (${MQTT_USER}/${MQTT_PASS})"
    echo "     TCP Server: 0.0.0.0:9000"
    echo ""
    echo "  🔑 数据库密码: ${DB_PASS}"
    echo "  🔑 MQTT 密码:  ${MQTT_PASS}"
    echo "  🔑 JWT Secret: ${JWT_SECRET}"
    echo ""
    echo "  ⚠️  请妥善保管以上密码信息!"
    echo ""
    echo "  📖 常用命令:"
    echo "     查看后端状态: systemctl status iot-monitor"
    echo "     查看后端日志: journalctl -u iot-monitor -f"
    echo "     重启后端:     systemctl restart iot-monitor"
    echo "     Docker 容器:  ${CONTAINER_CMD} ps"
    echo "     查看 TDengine: ${CONTAINER_CMD} logs tdengine"
    echo "     查看 EMQX:    ${CONTAINER_CMD} logs emqx"
    echo ""
    echo "============================================================"
}

# ============ 主流程 ============
main() {
    echo ""
    echo "============================================================"
    echo "  IoT-Monitor 一键部署脚本 (CentOS Stream 10)"
    echo "============================================================"
    echo ""

    check_root
    check_os

    setup_system
    setup_postgresql
    setup_tdengine
    setup_redis
    setup_emqx
    setup_python
    deploy_app
    init_database
    setup_systemd
    setup_nginx
    start_services
    print_summary
}

# 允许通过环境变量覆盖配置
# sudo -E DB_PASS=xxx ADMIN_PASS=xxx DOMAIN=xxx bash deploy.sh
main "$@"
