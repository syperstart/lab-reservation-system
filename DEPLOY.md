# 智能实验室预约系统 · 腾讯云部署手册

> 目标：把「Vue3 前端 + FastAPI 后端 + MySQL」部署到一台腾讯云 CVM，用 Nginx 统一对外。
> 项目结构（服务器上）：`/opt/lab/cursor/backend`、`/opt/lab/cursor/frontend`

## 一、架构

```
用户浏览器
   │  80 / 443
   ▼
Nginx（公网入口）
   ├── /            → 前端静态文件 cursor/frontend/dist
   ├── /api/        → 反向代理 127.0.0.1:8000（FastAPI）
   └── /uploads/    → 反向代理 127.0.0.1:8000（头像/图片）
                       │
                       ▼
              FastAPI（uvicorn，systemd 守护）
                       │
                       ▼
                MySQL 127.0.0.1:3306
```

**安全原则**：8000 端口只监听 `127.0.0.1`，安全组**不要**对外开 8000。

---

## 二、买服务器 & 安全组

| 项 | 建议 |
|---|---|
| 机型 | 2 核 4G（2 核 2G 也能跑，chromadb + 后端会吃点内存） |
| 系统 | **Ubuntu 24.04 LTS**（自带 Python 3.12，最省事）或 Ubuntu 22.04 |
| 安全组 | 放行 **22**（SSH）、**80**（HTTP）、**443**（HTTPS）；**不要**放行 8000 |

记录公网 IP，例如 `1.2.3.4`。

---

## 三、连接服务器

```bash
ssh root@1.2.3.4
```

---

## 四、安装依赖

```bash
apt update
apt install -y python3 python3-venv python3-pip nginx mysql-server git curl build-essential python3-dev

# Node.js 22 LTS
curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
apt install -y nodejs
node -v && npm -v
```

> 国内机器如果 NodeSource 慢，可换腾讯云镜像或直接用 `apt install -y nodejs npm`（版本可能偏老，需 ≥ 20.19）。

---

## 五、把代码放到服务器

推荐用 Git：

```bash
mkdir -p /opt/lab && cd /opt/lab
git clone <你的仓库地址> .
# 没有仓库就用 sftp / WinSCP / XFTP 把整个项目上传到 /opt/lab
```

确保目录是：
```
/opt/lab/cursor/backend/
/opt/lab/cursor/frontend/
```

---

## 六、建 MySQL 数据库

```bash
mysql -uroot -p
```

```sql
CREATE DATABASE `lab-agent` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
CREATE USER 'lab'@'localhost' IDENTIFIED BY '换成强密码';
GRANT ALL PRIVILEGES ON `lab-agent`.* TO 'lab'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

> 库名带连字符 `-`，SQL 里必须用反引号包起来。

> 建表、演示数据都**不用手动导入**：后端启动时会自动建表，并在表为空时写入 4 个实验室 + 8 台设备。

---

## 七、后端部署

```bash
cd /opt/lab/cursor/backend

# 1) 建虚拟环境、装依赖
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2) 配置 .env
cp .env.example .env
nano .env
```

`.env` 必改项：

```ini
DATABASE_URL=mysql+pymysql://lab:你的数据库密码@127.0.0.1:3306/lab-agent?charset=utf8mb4
SECRET_KEY=用下面命令生成
LM_API_KEY=你的 DeepSeek Key
LM_BASE_URL=https://api.deepseek.com
LM_MODEL=deepseek-chat
```

生成随机密钥：
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

**3) 先手动跑一次，确认能起来**
```bash
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

看到这三行就成功：
```
[启动] 数据库表已就绪
[启动] 演示数据已就绪（若表已有数据则跳过）
[启动] RAG 知识库已加载：75 条
```
按 `Ctrl+C` 停掉，改走 systemd。

---

## 八、用 systemd 守护后端

新建 `/etc/systemd/system/lab-backend.service`：

```ini
[Unit]
Description=Lab Reservation Backend
After=network.target mysql.service

[Service]
User=root
WorkingDirectory=/opt/lab/cursor/backend
Environment="PATH=/opt/lab/cursor/backend/.venv/bin"
ExecStart=/opt/lab/cursor/backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload
systemctl enable --now lab-backend
systemctl status lab-backend      # 看到 active (running) 即可
journalctl -u lab-backend -f      # 看日志
```

> 生产不要用 `--reload`；`--workers 1` 即可（RAG 索引在内存里，多 worker 会各建一份、内存翻倍）。

---

## 九、前端构建

```bash
cd /opt/lab/cursor/frontend
npm install
npm run build
```

产物在 `/opt/lab/cursor/frontend/dist`。

> `vite.config.ts` 里的 `/api`、`/uploads` 代理只在开发时用；生产由 Nginx 代理，不影响构建。

---

## 十、Nginx 配置

新建 `/etc/nginx/sites-available/lab.conf`：

```nginx
server {
    listen 80;
    server_name 1.2.3.4;          # 有域名就填域名

    root /opt/lab/cursor/frontend/dist;
    index index.html;

    # 前端 SPA：找不到文件就回 index.html（刷新不 404）
    location / {
        try_files $uri $uri/ /index.html;
    }

    # 后端 API
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        client_max_body_size 20m;     # 头像上传
    }

    # 上传的图片
    location /uploads/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
    }
}
```

启用 + 重载：

```bash
ln -s /etc/nginx/sites-available/lab.conf /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t            # 语法检查，必须 OK
systemctl reload nginx
```

---

## 十一、验证

1. 浏览器打开 `http://1.2.3.4` → 应看到登录页；
2. 用 `admin / admin`（管理员）或 `student01 / 123456`（学生）登录；
3. 试「AI 智能助手」问「有哪些实验室」→ 应返回真实实验室；
4. 试预约、上传头像、刷新页面不 404。

排查命令：
```bash
netstat -tlnp | grep 8000          # 后端在听 127.0.0.1:8000
curl http://127.0.0.1:8000/health  # 后端健康检查
journalctl -u lab-backend -n 50    # 后端日志
tail -f /var/log/nginx/error.log   # Nginx 错误日志
```

---

## 十二、可选：域名 + HTTPS

1. 域名需在**腾讯云备案**（未备案不能绑定 80/443 到域名；用 IP 访问一般可用）；
2. 证书：
```bash
apt install -y certbot python3-certbot-nginx
certbot --nginx -d 你的域名
```
自动改成 443 并配置续期。

---

## 十三、常见坑

| 现象 | 原因 | 处理 |
|---|---|---|
| 首页 404 / 刷新 404 | 没配 `try_files ... /index.html` | 见 Nginx 配置 |
| 接口 502 | 后端没起 / 端口不对 | `systemctl status lab-backend`、`curl /health` |
| 接口 404 | Nginx 少了 `/api/` 反代 | 检查 location |
| 上传图片 404 | 少了 `/uploads/` 反代 | 检查 location |
| 登录接口 500 | 数据库连不上 | 检查 `.env` 的 DATABASE_URL、MySQL 是否运行 |
| 中文乱码 | 库/表不是 utf8mb4 | 建库时用 utf8mb4 |
| pip 装 chromadb 失败 | 缺编译工具 | `apt install build-essential python3-dev` |
| Python 太老 | Ubuntu 22.04 自带 3.10 | 装 3.11/3.12，或直接用 Ubuntu 24.04 |
| 前端构建报 Node 版本 | Vite 8 要求 Node ≥20.19 | 装 Node 22 LTS |

---

## 十四、日常更新流程

```bash
cd /opt/lab
git pull

# 后端有改动
cd cursor/backend && .venv/bin/pip install -r requirements.txt
systemctl restart lab-backend

# 前端有改动
cd ../frontend && npm install && npm run build
# Nginx 直接读 dist，无需重启
```
