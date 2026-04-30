#!/bin/bash
# ============================================================
#  IoT-Monitor 一键部署脚本 (CentOS Stream 10)
#
#  使用: sudo bash deploy.sh
#
#  功能:
#    1. 安装系统依赖
#    2. 安装并配置 PostgreSQL
#    3. 安装并配置 TDengine
#    4. 安装并配置 Redis
#    5. 安装并配置 EMQX (MQTT Broker)
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

# ============ 1. 系统基础 ============
setup_system() {
    info "配置系统基础环境..."

    dnf update -y -q
    dnf install -y -q wget curl git vim tar gcc gcc-c++ make \
        epel-release yum-utils policycoreutils-python-utils

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

# ============ 3. TDengine ============
setup_tdengine() {
    info "安装 TDengine..."

    if ! command -v taosd &>/dev/null; then
        TDENGINE_RPM="TDengine-server-3.3.4.3-x86_64.rpm"
        if [ ! -f "/tmp/${TDENGINE_RPM}" ]; then
            wget -q -O "/tmp/${TDENGINE_RPM}" \
                "https://www.taosdata.com/assets-download/3.0/${TDENGINE_RPM}" || \
                warn "TDengine 下载失败，请手动安装"
        fi
        if [ -f "/tmp/${TDENGINE_RPM}" ]; then
            rpm -ivh "/tmp/${TDENGINE_RPM}" 2>/dev/null || true
        fi
    fi

    systemctl enable --now taosd 2>/dev/null || true
    systemctl enable --now taosadapter 2>/dev/null || true

    # 创建数据库
    sleep 2
    taos -s "CREATE DATABASE IF NOT EXISTS ${TDENGINE_DB} KEEP 365 DURATION 30 BUFFER 16 WAL_LEVEL 1 PRECISION 'ms';" 2>/dev/null || \
        warn "TDengine 数据库创建失败，稍后由应用自动创建"

    ok "TDengine 安装完成"
}

# ============ 4. Redis ============
setup_redis() {
    info "安装 Redis..."

    dnf install -y -q redis
    systemctl enable --now redis

    redis-cli ping | grep -q PONG || warn "Redis 启动异常"
    ok "Redis 安装完成"
}

# ============ 5. EMQX ============
setup_emqx() {
    info "安装 EMQX..."

    if ! command -v emqx &>/dev/null; then
        cat > /etc/yum.repos.d/emqx.repo <<'REPO'
[emqx]
name=emqx
baseurl=https://repos.emqx.io/emqx-ce/rpm/el/9/$basearch
enabled=1
gpgcheck=0
REPO
        dnf install -y -q emqx 2>/dev/null || warn "EMQX 安装失败，请手动安装"
    fi

    systemctl enable --now emqx 2>/dev/null || true

    # 等待 EMQX 启动
    sleep 5

    # 创建 MQTT 用户
    if command -v emqx_ctl &>/dev/null; then
        emqx_ctl users add ${MQTT_USER} ${MQTT_PASS} 2>/dev/null || true
    fi

    ok "EMQX 安装完成 (MQTT用户: ${MQTT_USER})"
}

# ============ 6. Python 环境 ============
setup_python() {
    info "安装 Python 环境..."

    dnf install -y -q python3.11 python3.11-devel python3-pip 2>/dev/null || \
        dnf install -y -q python3 python3-devel python3-pip

    PYTHON_CMD="python3.11"
    command -v python3.11 &>/dev/null || PYTHON_CMD="python3"

    ok "Python 安装完成 ($(${PYTHON_CMD} --version))"
}

# ============ 7. 部署应用 ============
deploy_app() {
    info "部署后端应用..."

    # 克隆代码
    if [ -d "${APP_DIR}" ]; then
        cd "${APP_DIR}"
        git pull origin master
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

    # 设置环境变量供 init_db.py 使用
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
After=network.target postgresql.service taosd.service redis.service emqx.service
Wants=postgresql.service taosd.service redis.service emqx.service

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

    # API 代理
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 300;
        proxy_connect_timeout 60;
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

    # 静态文件缓存
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf)$ {
        proxy_pass http://127.0.0.1:8000;
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
    systemctl restart taosd 2>/dev/null || true
    systemctl restart redis
    systemctl restart emqx 2>/dev/null || true
    sleep 3
    systemctl start iot-monitor
    systemctl restart nginx

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
    echo "     TDengine:   localhost:6030 (${TDENGINE_DB})"
    echo "     Redis:      localhost:6379"
    echo "     EMQX MQTT:  localhost:1883"
    echo "     TCP Server: 0.0.0.0:9000"
    echo ""
    echo "  🔑 数据库密码: ${DB_PASS}"
    echo "  🔑 MQTT 密码:  ${MQTT_PASS}"
    echo "  🔑 JWT Secret: ${JWT_SECRET}"
    echo ""
    echo "  ⚠️  请妥善保管以上密码信息!"
    echo ""
    echo "  📖 常用命令:"
    echo "     查看状态: systemctl status iot-monitor"
    echo "     查看日志: journalctl -u iot-monitor -f"
    echo "     重启服务: systemctl restart iot-monitor"
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
# DB_PASS=xxx ADMIN_PASS=xxx DOMAIN=xxx sudo -E bash deploy.sh
main "$@"
