# 智能预约系统 · 后端（FastAPI + MySQL）

## 目录结构

```
backend/
├── .venv/                  Python 虚拟环境
├── .env                    ★ 存 API 配置 + 数据库连接串（含密码，不进 Git）
├── .env.example            .env 模板，不含真实密码，可提交
├── main.py                 兼容入口（薄包装层，转发到 app/main.py）
├── requirements.txt        依赖清单
├── .gitignore              忽略 .venv / __pycache__ / .env
├── README.md
├── DEVELOPMENT.md          唯一开发路线文档（每次开发同步更新）
└── app/                    Python 包
    ├── __init__.py         让 app 成为包
    ├── main.py             ★ FastAPI 主应用：启动、建表、注册路由、健康检查
    ├── config.py           ★ 读取 .env，生成 settings 配置对象
    ├── database.py         ★ 数据库引擎、会话、公共父类 Base、建表函数
    ├── model/              数据模型（表）文件夹
    │   ├── __init__.py     让 model 成为包
    │   └── user.py         ★ 用户表模型
    ├── schemas/            数据模板（输入 / 输出）
    │   ├── __init__.py
    │   ├── auth.py         ★ 登录请求模板 LoginRequest
    │   └── user.py         ★ 用户响应模板 UserResponse
    ├── utils/              工具函数
    │   ├── __init__.py
    │   └── jwt.py         ★ create_access_token 生成 JWT token
    └── api/                接口层
        ├── __init__.py
        └── auth.py         ★ 登录接口 POST /api/auth/login
```

> 四个新建文件里的**每一行代码都写了中文注释**，按顺序读 `.env → config.py → database.py → model/user.py` 就能理解整条链路。

## 四个文件的职责

| 文件 | 作用 |
| --- | --- |
| `.env` | 专门放 API 配置（标题、前缀、密钥、第三方 Key）和 `DATABASE_URL` 数据库连接串 |
| `app/config.py` | 用 `pydantic-settings` 把 `.env` 读成 `settings` 对象，其它文件统一 `from app.config import settings` |
| `app/database.py` | 用 `settings.DATABASE_URL` 建引擎、会话工厂、`get_db()`，并定义所有表共用的 `Base`（`id / create_time / update_time`）和 `init_db()` |
| `app/model/user.py` | 定义 `User` 类 → MySQL 的 `user` 表，字段：账号、姓名、密码、角色、邮箱、手机号、头像、状态 |

`app/main.py` 是真正的入口：启动时调用 `init_db()` 自动建表，注册 `api/auth.py` 的登录路由，
`/health` 会同时检查依赖和数据库连通性；根目录的 `main.py` 只是兼容旧命令的转发壳。

## .env 里的数据库配置

```
DATABASE_URL=mysql+pymysql://root:123456@127.0.0.1:3306/lab-agent?charset=utf8mb4
```

| 部分 | 含义 |
| --- | --- |
| `mysql+pymysql` | 用 SQLAlchemy + PyMySQL 驱动连 MySQL |
| `root:123456` | 用户名 / 密码；账号是 `root`，**不是 `rooot`**（MySQL 里没有这个用户） |
| `127.0.0.1:3306` | 本机 MySQL 9.0 服务 |
| `lab-agent` | 你在 Navicat 里创建好的库，名字中间有连字符 `-` |
| `charset=utf8mb4` | 支持中文和 emoji |

## JWT 环境变量（登录令牌）

`.env` 的「二、JWT 登录令牌配置」分区放了 4 项，`app/config.py` 会自动读取：

| 变量 | 当前值 | 作用 |
| --- | --- | --- |
| `SECRET_KEY` | 随机生成的强密钥（不在此展示） | 给 token 签名，泄露 = 别人能伪造登录 |
| `ALGORITHM` | `HS256` | 签名算法，同一把密钥签名与校验 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | 访问令牌有效期（分钟） |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | 刷新令牌有效期（天），暂时预留 |

换一把新密钥：

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

把输出粘到 `.env` 的 `SECRET_KEY=` 后面，重启服务即可。`.env` 已被 `.gitignore` 忽略，
`.env.example` 里只有占位文字，可以安全提交。

签发 / 校验用 `PyJWT`：

```python
from datetime import datetime, timedelta, timezone
import jwt
from app.config import settings

exp = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
token = jwt.encode({"sub": "admin", "exp": exp}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
data = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])  # {'sub':'admin','exp':...}
```

### 封装好的工具函数

上面是原理，实际项目里直接用 `app/utils/jwt.py`：

```python
from app.utils.jwt import create_access_token

token = create_access_token(user_id=1)   # 内含 user_id 和 1 小时后过期的 exp
```

`app/config.py` 另加了 `JWT_SECRET_KEY` / `JWT_ALGORITHM` / `JWT_EXPIRE_HOURS`
三个只读别名，映射到上面那几个 `.env` 变量，方便照抄教学视频的代码；
`.env` 里不用再加第二套 JWT 配置。

## 和 Navicat 的关系

**代码不需要连接 Navicat。** Navicat 只是一个「看数据库的窗口」，它和 Python 后端连的是
同一台 MySQL 服务器、同一个 `lab-agent` 库。后端通过 PyMySQL 直连 `127.0.0.1:3306`
建表 / 写入数据后，在 Navicat 左侧选中 `lab-agent` → 右键「刷新」（或按 F5），
就能看到 `user` 表和里面的数据。

> 之前测试用的 `appointment_db` 库仍在（里面也有一张 user 表），不影响现在这个库。
> 另外 MySQL 里还有一个空的 `la-agent` 库，疑似创建时多建了一次，未做任何改动。

## 激活虚拟环境

```bash
# Git Bash
source .venv/Scripts/activate
# PowerShell
.\.venv\Scripts\Activate.ps1
```

## 启动与验证

```bash
uvicorn app.main:app --reload          # 推荐（在 backend 目录下执行）
# 老命令仍然可用：uvicorn main:app --reload
# 或：python main.py
```

> **注意**：以前只有 `backend/main.py`，那时敲 `uvicorn app.main:app` 会报
> `Could not import module "app.main"`。现在主应用已迁到 `app/main.py`，
> 根目录 `main.py` 保留为兼容层，两条命令都能启动、拿到的是同一个 app。

> **另一个常见坑：浏览器显示「127.0.0.1 拒绝了连接」**
> 直接敲 `uvicorn` 会调用系统全局 Python 3.11 的那个，它缺 `pydantic_settings`、
> `pymysql`，应用导入失败、进程挂着却不监听端口。PowerShell 里请显式调用项目虚拟环境的 exe：
>
> ```powershell
> cd D:\智能预约系统\cursor\backend
> .\.venv\Scripts\uvicorn.exe app.main:app --reload
> ```
>
> 窗口保持开着（不要关、不要按 Ctrl+C），再打开 <http://127.0.0.1:8000/docs>。
> 判断服务是否真的起来了：`netstat -ano | findstr 8000` 要看到 `LISTENING`。

**Cursor 编辑器也要切到同一个解释器**：工作区根的 `.vscode/settings.json` 已把
`python.defaultInterpreterPath` 指向项目 `.venv`，并加了 `python.analysis.extraPaths`，
这样 `from app.config import settings` 不会再画红线。若 Cursor 打开的是 `cursor` 子目录，
需手动 `Ctrl+Shift+P → Python: Select Interpreter` 选
`cursor\backend\.venv\Scripts\python.exe`。

> 本机同时有 3 个 Python：全局 3.11（裸命令 `uvicorn` / `python` 会命中它，缺
> `pydantic_settings` / `pymysql` / `PyJWT`）、编辑器里的 3.14、项目 `.venv` 的 3.13.14。
> **只用 `.venv`**；看到 `ModuleNotFoundError` 先查解释器，不要改 `app/` 下的代码。

**编辑器里的 import 红线**：`from app.xxx import ...` 画红线是 Pylance 没找到项目包和依赖，
不是代码错。三个候选工作区根（`D:\智能预约系统`、`cursor`、`cursor\backend`）都放了
`.vscode/settings.json` + `pyrightconfig.json`，`extraPaths` 直接指向
`.venv/Lib/site-packages`；若仍显示红线，执行一次
`Ctrl+Shift+P → Python: Restart Language Server`（或 Reload Window）即可。

打开：

- <http://127.0.0.1:8000/docs> 接口文档（里面能看到「权限验证」分组下的登录接口）
- <http://127.0.0.1:8000/health> 返回 `"database": {"status": "ok"}` 就说明连库成功

测试登录接口：

```bash
curl -X POST http://127.0.0.1:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}'
# 成功返回 {"code":200,"message":"操作成功","data":{...},
#           "access_token":"eyJ...","token_type":"bearer"}
# 密码错误返回 {"code":400,"message":"账号或密码错误"}（不含 token）
```

> 登录密码由 `app/utils/password.py` 用 bcrypt 校验（依赖 `bcrypt` 已写进 requirements.txt）。
> `lab-agent.user` 里 3 条示例用户目前仍是明文密码，工具函数已做兼容；
> 以后把密码换成 `hash_password()` 生成的哈希，代码不用改。

查看用户表结构：

```bash
mysql -u root -p123456 -e 'DESC `lab-agent`.`user`; SELECT * FROM `lab-agent`.`user`;'
```

`lab-agent`.`user` 里目前有 3 条示例数据（`admin / student01 / student02`），
用来验证写入链路是否正常；不需要时可以直接删掉。

## 依赖

```bash
python -m pip install -r requirements.txt
```

主要包：`fastapi`、`uvicorn[standard]`、`python-multipart`、`SQLAlchemy`、`PyMySQL`、
`pydantic-settings`、`PyJWT`。

## 安全提醒（正式上线前要改）

1. `.env` 里是明文密码，已加入 `.gitignore`，不要提交、不要发给别人。
2. `SECRET_KEY` 目前是开发用默认值，上线前换成随机字符串。
3. `user.password` 现在按参考图存字符串，正式项目应存哈希（bcrypt），并把 `String(50)` 改成 `String(255)`。
4. `123456` 是弱密码，只适合本机开发。
