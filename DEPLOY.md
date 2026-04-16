# SuperPipeline 部署规格书 — 云服务器 + 域名 + 账户认证

> 状态：规划中
> 目标：将 SuperPipeline 前后端部署到云服务器，通过域名访问，支持账户密码登录

---

## 0. 需求概述

### 最终目标
- 将 SuperPipeline (FastAPI 后端 + Next.js 前端) 部署到 `root@152.136.151.58`
- 通过域名访问（如 `https://pipeline.yourdomain.com`）
- 添加账户密码认证，中间层保护（白名单 IP 可直接访问）
- 支持远程 AI 写文章 + 用户从网站复制内容

### 技术栈
- **后端**：FastAPI (Python 3.12) + SQLite
- **前端**：Next.js 16 (React 19)
- **反向代理 / HTTPS**：Nginx + Let's Encrypt
- **进程管理**：systemd (后端) + Node 原生管理 (前端)
- **认证**：Nginx IP 白名单 + HTTP Basic Auth 双重保护
- **域名**：需用户自行配置 DNS A 记录指向 `152.136.151.58`

---

## 1. 服务器环境准备

### 1.1 系统依赖

```bash
# Ubuntu 22.04 LTS
apt update && apt upgrade -y
apt install -y python3.12 python3.12-venv python3-pip git curl ufw nginx certbot python3-certbot-nginx
```

### 1.2 目录结构

```
/opt/superpipeline/
├── server/                 # 后端代码 (git clone 的 workspace)
│   ├── src/
│   ├── server/
│   ├── config.yaml
│   ├── .venv/              # Python 虚拟环境
│   └── data/
│       └── pipeline.db      # SQLite 数据库
├── web/                    # 前端代码
│   ├── src/
│   └── .next/
└── logs/
    ├── server.log          # FastAPI 日志
    └── web.log             # Next.js 日志
```

### 1.3 防火墙

```bash
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP (Let's Encrypt 用)
ufw allow 443/tcp   # HTTPS
ufw enable
```

---

## 2. 代码部署

### 2.1 拉取代码

在服务器上操作（假设代码在 GitHub）：

```bash
cd /opt
git clone https://github.com/YOUR_GITHUB/superpipeline.git
cd superpipeline/server
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt  # 或 requirements.lock
```

### 2.2 后端配置

创建 `/opt/superpipeline/server/config.yaml`：

```yaml
storage:
  db_path: /opt/superpipeline/server/data/pipeline.db
  assets_dir: /opt/superpipeline/server/data/assets
  outputs_dir: /opt/superpipeline/server/outputs

models:
  text:
    provider: minimax
    model: MiniMax-Text-01
    api_key: ${MINIMAX_API_KEY}
    base_url: https://api.minimax.chat

app:
  host: 127.0.0.1
  port: 8000
  debug: false
```

环境变量文件 `/opt/superpipeline/server/.env`：

```
MINIMAX_API_KEY=your_api_key_here
SP_CONFIG=/opt/superpipeline/server/config.yaml
SP_PIPELINES_DIR=/opt/superpipeline/server/pipelines
```

### 2.3 验证后端

```bash
cd /opt/superpipeline/server
source .venv/bin/activate
python -c "from src.api.app import create_app; print('OK')"
```

---

## 3. 前端构建

```bash
cd /opt/superpipeline/web
npm install
npm run build

# 设置 API 基础URL（在 .env.local）
echo "NEXT_PUBLIC_API_URL=https://pipeline.yourdomain.com" > .env.local
```

---

## 4. 认证方案 — Nginx IP 白名单 + HTTP Basic Auth

### 为什么这样设计
- 飞书 AI 可以从任意 IP 调用 API → 用 HTTP Basic Auth 保护
- 月明自己的电脑 → IP 白名单直接过，简化操作
- FastAPI 不改一行代码，认证全在 Nginx 层

### 4.1 创建密码文件

```bash
# 安装 apache2-utils (包含 htpasswd)
apt install -y apache2-utils

# 创建密码文件（用户: ai, 密码: 你设的）
htpasswd -bc /etc/nginx/.htpasswd ai your_password_here

# 添加第二个用户（月明自己的账号）
htpasswd -b /etc/nginx/.htpasswd moon your_moon_password
```

### 4.2 配置 IP 白名单文件

创建 `/etc/nginx/whitelist.conf`：

```
# 月明自己的电脑 IP（你后续告诉我，我填上）
allow 120.0.0.1;
allow 127.0.0.1;
# 你后续补充的 IP
allow YOUR_HOME_IP;

# 其他 IP 全 deny（但 Basic Auth 通过后可以访问）
satisfy any;
```

### 4.3 Nginx 配置

创建 `/etc/nginx/sites-available/superpipeline`：

```nginx
server {
    listen 80;
    server_name pipeline.yourdomain.com;

    # Let's Encrypt 用
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name pipeline.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/pipeline.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/pipeline.yourdomain.com/privkey.pem;

    root /opt/superpipeline/web/.next;
    index index.html;

    # 日志
    access_log /var/log/nginx/superpipeline_access.log;
    error_log /var/log/nginx/superpipeline_error.log;

    # 静态资源 (Next.js build)
    location /_next/ {
        alias /opt/superpipeline/web/.next/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # API 代理 — 受保护
    location /api/ {
        # IP 白名单 + Basic Auth 双重验证
        auth_basic "SuperPipeline API - Contact Moon";
        auth_basic_user_file /etc/nginx/.htpasswd;

        satisfy any;
        include /etc/nginx/whitelist.conf;
        deny all;

        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSE 支持
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 86400;
    }

    # 前端页面 — 也保护起来
    location / {
        auth_basic "SuperPipeline";
        auth_basic_user_file /etc/nginx/.htpasswd;

        satisfy any;
        include /etc/nginx/whitelist.conf;
        deny all;

        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 4.4 启用站点 + SSL

```bash
ln -s /etc/nginx/sites-available/superpipeline /etc/nginx/sites-enabled/
nginx -t
systemctl reload nginx

# 申请 SSL 证书（需要域名已解析到服务器）
certbot --nginx -d pipeline.yourdomain.com
```

---

## 5. 进程管理 — systemd

### 5.1 后端服务

创建 `/etc/systemd/system/superpipeline-server.service`：

```ini
[Unit]
Description=SuperPipeline FastAPI Backend
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/superpipeline/server
EnvironmentFile=/opt/superpipeline/server/.env
ExecStart=/opt/superpipeline/server/.venv/bin/python -m uvicorn src.api.app:create_app --factory --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5
StandardOutput=append:/opt/superpipeline/logs/server.log
StandardError=append:/opt/superpipeline/logs/server.log

[Install]
WantedBy=multi-user.target
```

### 5.2 前端服务

Next.js 用 systemd 管理：

创建 `/etc/systemd/system/superpipeline-web.service`：

```ini
[Unit]
Description=SuperPipeline Next.js Frontend
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/superpipeline/web
ExecStart=/usr/bin/npm start
Restart=always
RestartSec=5
StandardOutput=append:/opt/superpipeline/logs/web.log
StandardError=append:/opt/superpipeline/logs/web.log
Environment=NODE_ENV=production
Environment=PORT=3000

[Install]
WantedBy=multi-user.target
```

### 5.3 启动服务

```bash
systemctl daemon-reload
systemctl enable superpipeline-server
systemctl enable superpipeline-web
mkdir -p /opt/superpipeline/logs
systemctl start superpipeline-server
systemctl start superpipeline-web
systemctl status superpipeline-server
systemctl status superpipeline-web
```

---

## 6. 部署检查清单

```bash
# 1. 确认服务运行
curl http://127.0.0.1:8000/health          # 后端健康检查
curl http://127.0.0.1:8000/api/pipelines   # API 测试

# 2. 确认 Nginx 反向代理
curl -I https://pipeline.yourdomain.com/api/pipelines

# 3. 确认 SSL
certbot certificates

# 4. 日志检查
journalctl -u superpipeline-server -f
journalctl -u superpipeline-web -f
tail -f /opt/superpipeline/logs/server.log
```

---

## 7. 远程 AI 调用方式

认证通过后，AI 通过 HTTP Basic Auth 调用：

```bash
curl -u ai:your_password_here \
  -X POST https://pipeline.yourdomain.com/api/runs \
  -H "Content-Type: application/json" \
  -d '{
    "pipeline": "douyin",
    "brief": "写一篇关于 AI 编程助手使用技巧的文章",
    "keywords": ["AI", "编程助手", "效率"]
  }'
```

---

## 8. 月明需要做的事

1. **域名**：购买/配置一个域名，将 `pipeline.yourdomain.com` A 记录指向 `152.136.151.58`
2. **IP 白名单**：告诉我你家宽 IP，我写入 `/etc/nginx/whitelist.conf`
3. **SSL 证书**：域名解析生效后，运行 `certbot --nginx -d pipeline.yourdomain.com`
4. **密码**：设置 `ai` 账号的密码，告诉我（我会加密存储）

---

## 9. 不做什么

- 不做 OAuth / SSO（当前不需要）
- 不改 FastAPI 代码添加认证（Nginx 层统一处理）
- 不做 Docker（服务器资源有限，原生 Python + Node 更稳定）
- 不做负载均衡（单台够用）
