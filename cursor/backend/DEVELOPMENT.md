# 智能预约系统 · 开发路线文档

> **使用说明（本项目唯一一份开发路线文档）**
>
> 1. 只维护这一份，**不另建新 MD、不重写整篇**；每次有开发进展都在这里同步追加。
> 2. **和「谁做的」无关**：不管是我代你完成，还是**你自己手动创建 / 修改代码、配置、数据库**，
>    都算一步开发，都要记进来；不需要「必须让我做完」才能更新文档。
> 3. 你手动做完，只要说一句「我把 XX 做好了，记到文档里」，我就补上对应步骤；
>    你也可以**直接在这个文件里手写**。我下次更新前会**先读取文件现状**，
>    完整保留你手写的段落，只在末尾接着追加，不覆盖、不删改、不强行重排版。
> 4. 编号接着最后一个「第 N 步」往后排；手写时没写编号也没关系，不用刻意对齐。
>
> 阅读顺序：上面的「开发步骤」按时间顺序记录做了什么；下面的「项目结构」说明各模块职责和相互关系。

**自己手写一步时，可以直接复制这个格式：**

```md
### 第 N 步：这一步做了什么（自己完成）

- 做了什么：
- 涉及文件：
- 结果：
```

---

## 一、开发步骤（按时间顺序）

### 第 1 步：搭建 FastAPI 环境

- 在 `D:\智能预约系统\cursor\backend` 创建目录
- 用 `python -m venv .venv` 创建虚拟环境（Python 3.13.14）
- 安装 `fastapi`、`uvicorn[standard]`、`python-multipart`
- 创建 `main.py`，写一个 `/health` 健康检查接口，启动 `uvicorn main:app`

**结果**：后端能启动服务，`/docs` 出文档，`/health` 返回 OK。

---

### 第 2 步：修改本机 MySQL root 密码

- 本机 MySQL 9.0（3306），找回了原来的 root 密码（记在 finalshell.txt 里）
- 用 `ALTER USER 'root'@'localhost' IDENTIFIED BY '123456'` 改成 `123456`

**结果**：MySQL 可用，密码 `123456`。

---

### 第 3 步：创建 .env 文件

- 在 `backend/` 下新建 `.env`
- 里面分两部分：
  - **API 配置**：`API_TITLE`、`API_PREFIX`、`SECRET_KEY`、令牌时长、第三方 API Key
  - **数据库连接串**：`DATABASE_URL=mysql+pymysql://root:123456@127.0.0.1:3306/...`
- 加进 `.gitignore`，别提交密码

**结果**：所有配置集中在一处，密码不写进代码。

---

### 第 4 步：创建 `config.py`

- 用 `pydantic-settings` 读取 `.env`
- 输出全局对象 `settings`，别的文件统一用 `settings.DATABASE_URL`

**结果**：配置可以集中读取。

---

### 第 5 步：创建 `database.py`

- 用 `settings.DATABASE_URL` 创建 `engine`（连接池）
- 创建 `SessionLocal`（会话工厂）和 `get_db()`（接口里用 `Depends(get_db)` 拿会话）
- 定义公共父类 `Base`，带 `id / create_time / update_time` 三个公共列
- 加 `init_db()` 用来建表

**结果**：数据库连接通道就绪。

---

### 第 6 步：创建 `model/user.py`

- 定义 `User` 类继承 `Base`，对应数据库 `user` 表
- 字段：username / real_name / password / role / email / phone / avatar / status

**结果**：有了「用户表」的模型。

---

### 第 7 步：创建 `lab-agent` 数据库并写入数据

- 你在 Navicat 里创建了 `lab-agent` 库（账号 `root`，密码 `123456`）
- 把 `.env` 和 `config.py` 的连接串指向 `lab-agent`
- 执行 `init_db()` 建表
- 写入 3 条示例用户（admin / student01 / student02）

**结果**：`lab-agent.user` 表里有可登录的账号。

---

### 第 8 步：创建 `schemas/auth.py`

- 定义 `LoginRequest`：接收登录数据，只有 `username` + `password`

**结果**：登录接口有了「输入模板」。

---

### 第 9 步：创建 `schemas/user.py`

- 定义 `UserResponse`：返回用户数据，含 `id/name/email/phone/status`，不返回密码

**结果**：登录成功后的「输出模板」也准备好了。

---

### 第 10 步：创建 `api/auth.py`

- 写登录接口 `POST /api/auth/login`
- 收前端数据 → 查数据库 → 验密码 → 返回 `UserResponse`
- 用 `LoginRequest` 收数据，用 `UserResponse` 控制返回字段

**结果**：登录接口代码写完，但此时还没挂到主应用，`/docs` 里暂时看不到。

---

### 第 11 步：修复 `uvicorn app.main:app` 导入报错，统一后端入口

- **报错**：`ERROR: Error loading ASGI app. Could not import module "app.main"`
- **原因**：`uvicorn app.main:app` 要求存在 `backend/app/main.py`，
  但当时 FastAPI 应用写在 `backend/main.py` 根目录，`app.main` 这个模块根本不存在
- **处理**：
  1. 新建 `app/main.py`，把 FastAPI 应用（配置、CORS、lifespan 建表、`/`、`/health`）整体迁入
  2. 用 `app.include_router(auth_router)` 注册登录路由，`/docs` 里正式出现 `POST /api/auth/login`
  3. 根目录 `main.py` 改成薄包装层（只写 `from app.main import app`），
     老命令 `uvicorn main:app` 仍可用，两条命令拿到的是同一个 app 对象
  4. `python main.py` 内部也统一用 `app.main:app` 启动，避免热重载找错模块
- **验证**：`/health` 返回 `status ok`（11 个依赖齐全 + 数据库 `SELECT 1 成功`）；
  `admin/admin` 登录返回 `code 200` 与用户数据；错误密码返回 `code 400`；`/docs` 返回 200；
  启动日志出现 `[启动] 数据库表已就绪` 与 `Application startup complete`

**结果**：推荐启动命令固定为 `uvicorn app.main:app --reload`，登录接口已可被前端调用。

---

### 第 12 步：排查浏览器 `ERR_CONNECTION_REFUSED`（启动用错 Python 环境）

- **现象**：浏览器打开 `127.0.0.1:8000` 显示「127.0.0.1 拒绝了连接」，但任务管理器里能看到 uvicorn 进程
- **排查**：`netstat -ano | findstr 8000` 显示没有任何监听；查进程命令行发现跑的是
  `C:\Program Files\Python311\Scripts\uvicorn.exe app.main:app --reload`
- **原因**：调用的是系统全局 Python 3.11 的 uvicorn，而不是项目 `.venv`（Python 3.13.14）。
  全局环境只装了 fastapi / SQLAlchemy，缺 `pydantic_settings`、`pymysql`，
  `app.config` 一导入就抛 `ModuleNotFoundError`，应用没加载成功，所以进程挂着却不监听端口
- **处理**：停掉失败残留进程；改显式调用 `.venv\Scripts\uvicorn.exe app.main:app --reload`
- **验证**：8000 端口 LISTENING；`/` 返回入口 JSON；`/health` status ok（Python 3.13.14 +
  SELECT 1 成功）；`/docs` 200

**结果**：启动必须用项目虚拟环境的 uvicorn；浏览器访问 `/docs` 才是接口文档页，
根路径 `/` 只返回一段 JSON 文本。

---

### 第 13 步：配置 JWT 环境变量

- **目标**：登录成功后要发 token，签名密钥、算法、有效期统一放 `.env`，不写死在代码里
- `.env` 新增「二、JWT 登录令牌配置」分区，把原来散在 API 分区的
  `SECRET_KEY` / `ACCESS_TOKEN_EXPIRE_MINUTES` 归拢进来，字段不重复：

  | 变量 | 当前值 | 作用 |
  |---|---|---|
  | `SECRET_KEY` | 随机生成的 43 位字符串 | 给 token 签名，泄露等于别人能伪造登录 |
  | `ALGORITHM` | `HS256` | 签名算法（同一把密钥签名 + 校验） |
  | `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | 访问令牌有效期（分钟） |
  | `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | 刷新令牌有效期（天），为以后免重复登录预留 |

- `app/config.py` 增加 `ALGORITHM` / `REFRESH_TOKEN_EXPIRE_DAYS` 两个字段（逐行中文注释），
  其余字段不动；`pydantic-settings` 自动把 `.env` 里的字符串转成 int
- `.env.example` 同步这 4 项（密钥只放占位文字），并顺手把库名从旧的
  `appointment_db` 修正成 `lab-agent`
- 新装 `PyJWT==2.15.1`（项目 `.venv`，默认 PyPI 源），写进 `requirements.txt`；
  `pip check` 无冲突
- **验证**：`settings.ALGORITHM=HS256`、两个时长都是 `int`、密钥不再是默认占位值；
  用这套配置实际 `jwt.encode` 签发 + `jwt.decode` 校验通过；配置改动触发服务热重载后
  `/health` 仍返回 `status ok`

**结果**：JWT 环境变量已可用；下一步可写 `create_access_token()` 工具函数，
让登录接口成功后返回 token。

---

### 第 14 步：创建 `utils/jwt.py`（生成 JWT token）

- 按教学视频新建 `app/utils/__init__.py` + `app/utils/jwt.py`，写
  `create_access_token(user_id: int) -> str`：算过期时间 → 组装 payload → `jwt.encode` 签名
- **教程字段名和本项目不一致**：视频用 `settings.JWT_SECRET_KEY` / `JWT_ALGORITHM` /
  `JWT_EXPIRE_HOURS`，而 `.env` 里是 `SECRET_KEY` / `ALGORITHM` / `ACCESS_TOKEN_EXPIRE_MINUTES`。
  为了不出现「两把密钥、两套有效期」，在 `app/config.py` 加 3 个 `@property` 只读别名做映射
  （`JWT_EXPIRE_HOURS = ACCESS_TOKEN_EXPIRE_MINUTES / 60`），以后照抄教程代码不用改
- **照抄会踩的 3 个坑，已修正并写进逐行注释**：
  1. 视频 `import datetime` 却用 `datetime.now()` → 改成
     `from datetime import datetime, timedelta, timezone` + `datetime.now(timezone.utc)`，
     顺带避免本地时间被当成 UTC、有效期平白多 8 小时
  2. payload 里的 `"expire"` 不是 PyJWT 标准字段，token 会永不过期 → 改成 `"exp"`
  3. `datetime.timedelta(...)` → `timedelta(...)`
- **验证**：`create_access_token(1)` 返回 str；解码得 `{'user_id': 1, 'exp': ...}`，
  剩余有效期 3600 秒；过期 token 抛 `ExpiredSignatureError`、换密钥抛 `InvalidSignatureError`；
  `config.py` 改动触发热重载后 `/health` 仍 `status ok`

**结果**：工具函数可用；`api/auth.py` 目前还没调用它，下一步可让登录成功时返回 token。

---

### 第 15 步：排查 `ModuleNotFoundError: pydantic_settings`（解释器混用复发）

- **现象**：Cursor 终端再敲裸 `uvicorn app.main:app --reload`，报
  `No module named 'pydantic_settings'`，调用栈停在
  `app/main.py:25 → app/config.py:6`；编辑器里 `from app.config import settings` 也画红线
- **先查代码**：用项目 `.venv` 对 `app/` 跑 `compileall -q` 全部通过；
  `config / database / model.user / schemas.auth / schemas.user / api.auth / utils.jwt / main`
  共 8 个模块全部导入成功；pydantic-settings 2.16.2 存在；三个接口路由都注册着
  → **结论：app 下代码没问题，是解释器用错**
- **三个 Python 对比**：

  | 解释器 | 版本 | 关键依赖 | 谁在用 |
  |---|---|---|---|
  | `C:\Program Files\Python311` | 3.11.9 | 缺 `pydantic_settings` / `pymysql` / `PyJWT` | 裸 `uvicorn` / `python` 命令 |
  | `C:\Users\...\Python314` | 3.14.2 | 齐全 | Cursor 编辑器曾选中它 |
  | `cursor\backend\.venv` | 3.13.14 | 齐全 | **项目唯一该用的** |

- **处理**：
  1. 停掉后台验证实例，释放 8000 端口（避免你自己启动时提示「端口已被占用」）
  2. 新建 `D:\智能预约系统\.vscode\settings.json`：固定
     `python.defaultInterpreterPath` 到 `.venv`、`python.analysis.extraPaths` 指向 backend、
     集成终端自动激活环境，编辑器里的红线随之消失
  3. 启动命令仍固定 `.\.venv\Scripts\uvicorn.exe app.main:app --reload`
- **和第 12 步是同一个坑**：以后看到 `ModuleNotFoundError`，先查
  `Get-Command uvicorn` 命中的是哪个解释器，不要去改 `app/` 下的代码

**结果**：代码零改动；终端和编辑器统一只用 `.venv`。

---

### 第 16 步：密码校验（你自己手动完成的部分）+ 修掉新报错

> 按「使用说明」第 2 条：这一步是你**自己手动创建/修改**的，不是我代做的，同样同步进这份唯一文档。

- 你手动新建 `app/utils/password.py`：写了 `hash_password()` / `verify_password()`，用 bcrypt
- 你手动改 `app/api/auth.py`：引入 `verify_password`，把登录判断改成
  `if not user or not verify_password(data.password, user.password)`（这个 `not` 你自己补对了）
- 出现两个新问题：编辑器 **8 个错误**（状态栏仍是 Python 3.14，`app.*` 导入画红线）；
  启动时 `ModuleNotFoundError: No module named 'cursor'`
- **编辑器侧**：已有 `.vscode/settings.json`，再补 `pyrightconfig.json`
  （`extraPaths` 指向 backend、`venv` / `venvPath` 指向 `.venv`）；
  需 `Ctrl+Shift+P → Developer: Reload Window` 或手动 Select Interpreter 才生效
- **代码侧修正（完整保留你写的注释、函数结构、判断逻辑）**：
  1. 删掉误插入的 `from enum import verify`（enum 模块里没有 verify）
  2. `from cursor.backend.app.utils.password import ...` → `from app.utils.password import ...`
  3. `password.py`：`bcrypt.gensalt()` 原来误放进 `str.encode()` 的第二个参数（那是 errors 参数，
     只收字符串），改成 `bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())`；
     `checkpw` 原来只传一个参数、也没用 `hashed_password`，补齐成两个 bytes 参数
  4. 删掉 `auth.py` 里重复的明文比较，否则以后把密码换成哈希会永远登录失败
  5. `verify_password` 增加明文兼容：`lab-agent.user` 里 3 条示例用户仍是明文，
     不是 `$2a$ / $2b$ / $2y$` 开头就按明文比较，以后换哈希无需改代码
- 新装 `bcrypt==5.0.0`（项目 `.venv`），写进 `requirements.txt`；`pip check` 无冲突
- **验证**：模块全部导入成功；`hash_password` 返回 60 位 `$2b$` 哈希，
  正确 / 错误 / 明文兼容 / 空密码 5 个用例全通过；
  登录接口 `admin/admin` → 200、错误密码 → 400、不存在用户 → 400；`/health` ok

**结果**：服务能启动、登录链路走通；数据库示例密码仍是明文，
以后可用 `hash_password()` 批量换成哈希。

---

### 第 17 步：登录接口接入 JWT，成功时返回 `access_token`

- 在 `app/api/auth.py` 顶部加 `from app.utils.jwt import create_access_token`
- 登录成功时，在原有 `code / message / data`（用户信息）之外新增两个字段：
  `access_token`（由 `create_access_token(user.id)` 签发）和 `token_type: "bearer"`
- **刻意保持 `data` 原结构不变**：前端已有的用户信息取法不受影响；
  token 放在顶层，以后前端用请求头 `Authorization: Bearer <access_token>` 带上
- 失败时仍只返回 `{"code":400,"message":"账号或密码错误"}`，不签发 token
- **验证**：`admin/admin` 返回 200；解码 token 得 `{'user_id': 1, 'exp': ...}`，
  `user_id` 与 `data.id` 一致、剩余有效期 3599 秒（对应配置的 60 分钟）、
  `token_type=bearer`；错误密码响应里没有 `access_token`；`/health` ok、`/docs` 200
- 说明：字段名用 OAuth2 标准的 `access_token` / `token_type`；
  如果教学视频里叫 `token`，只需改一行返回字段名

**结果**：登录链路从「校验密码」走到「签发令牌」；
下一步可做「校验令牌」的依赖（保护其它业务接口），或把前端登录改成真实请求。

---

### 第 18 步：彻底解决编辑器 import 红线（配置没被 Pylance 读到）

- **现象**：`app/api/auth.py` 里 `from app.xxx import ...` 和
  `from sqlalchemy.orm import Session` 全部画红线，右上角 12 错误 1 警告，
  状态栏仍是 Python 3.14
- **前两次没修好的原因**：
  1. `.vscode/settings.json` / `pyrightconfig.json` 只放在 `D:\智能预约系统` 一层，
     而 Cursor 打开的工作区根可能是 `cursor` 或 `cursor\backend`，配置根本不在工作区根
  2. `python.defaultInterpreterPath` 只是「默认值」，之前手动选过 Python 3.14 后不生效
  3. 新建配置文件后没有重启 Pylance 语言服务
- **这次的处理**：
  1. 三个候选工作区根（`D:\智能预约系统`、`cursor`、`cursor\backend`）各放一份
     `.vscode/settings.json` + `pyrightconfig.json`，内容都用绝对路径，哪份生效都一样
  2. `extraPaths` 除了 backend，再加 `.venv/Lib/site-packages`：
     即使状态栏还显示 3.14，Pylance 也能直接找到 fastapi / sqlalchemy / bcrypt 等包
  3. 保留 `venvPath` + `venv` 指向 `.venv`、`pythonVersion: 3.13`
  4. `settings.json` 补 `python.analysis.autoSearchPaths: true`
- **必须做一次**：`Ctrl+Shift+P → Python: Restart Language Server`（或 Reload Window），
  Pylance 才会重新读取配置
- 说明：这些红线只是编辑器静态检查；代码用 `.venv` 实测全部导入成功、服务能启动、
  登录接口返回 200，**不影响运行**

**结果**：配置覆盖所有可能的工作区根；重启语言服务后红线消失。

**后续实证（用 Pyright CLI，与 Pylance 同一套引擎）**：
日志显示 `Loading configuration file at d:\智能预约系统\pyrightconfig.json`、
`Python version: 3.13`、`Found 17 source files`，最终
`errorCount: 0 / warningCount: 0`；单独检查 `app/api/auth.py` 也是 0 错误 0 警告。
也就是说**配置本身已正确**，Cursor 里残留的红线只需要重启 Pylance / Cursor 即可消除。

---

### 第 19 步：纠正编辑器对象 —— 实际是 PyCharm，不是 Cursor

> **重要更正**：第 15～18 步一直按「Cursor / Pylance」排查，方向是错的。
> 按「不删改」约定，那些段落原样保留，这里只补记真实结论。

- **查证**（枚举进程 + 窗口标题）：真正在开 `auth.py` 的是
  `D:\env\PyCharm 2025.1.3\bin\pycharm64.exe`，窗口标题 `智能预约系统 – auth.py`；
  本机没有运行 `Cursor.exe`，也没有 pylance / pyright 语言服务进程
- **为什么前几次没修好**：`.vscode/settings.json` / `pyrightconfig.json` /
  `pyproject.toml` 全是 VS Code / Cursor 的配置，PyCharm 一个都不读；
  Pyright CLI 实测 0 错误，是因为命令行读的是另一套配置，与 IDE 的诊断无关
- **真正原因**（问题面板 14 条「未解析的引用」）：
  1. 项目 SDK 是全局 `Python 3.14`，不是项目 `.venv`（3.13.14）
  2. `cursor/backend` 没被标为源码根，`from app.xxx import` 找不到 `app` 包
- **处理**（先备份到 `.workbuddy/backup/pycharm-20261105/`）：
  1. 全局 `AppData/Roaming/JetBrains/PyCharm2025.1/options/jdk.table.xml` 注册新 SDK
     `Python 3.13 (智能预约系统)` → `cursor/backend/.venv/Scripts/python.exe`
  2. `.idea/misc.xml` 的 `project-jdk-name`、`.idea/智能预约系统.iml` 的 `jdkName`
     一并指向该 SDK
  3. `.iml` 的 `<content>` 里加
     `<sourceFolder url="file://$MODULE_DIR$/cursor/backend" isTestSource="false" />`
  4. 正常关闭 PyCharm → 改配置 → 重新打开项目（关闭前标题无 `*`，无未保存内容）
- **过程中的两个环境坑**：Bash / Python 写 `AppData\Roaming\JetBrains` 下文件被拒
  （`PermissionError`），改由 PowerShell 通道执行同一脚本即可写入；
  `Start-Process` 不加 `-Wait` 时 IDE 会随命令结束被回收，加 `-Wait` 常驻后稳定
- **验证**（重启后截屏）：状态栏由 `Python 3.14` 变成 `Python 3.13 (智能预约系统)`，
  `from app.schemas.auth import LoginRequest` 等 import 行不再有红色波浪线，
  顶部只剩黄色警告；PyCharm 完成 `Updating skeletons`

**结果**：未解析引用的红线消除；以后这个项目改解释器只在 PyCharm 的
`Settings → Project → Python Interpreter` 里改，`.vscode` 那几份配置对此 IDE 无效。

---

### 第 20 步：创建 `dependencies/auth.py`（登录校验依赖）

- 按教学视频两张截图新建 `app/dependencies/__init__.py` + `app/dependencies/auth.py`，
  实现 `get_current_user(token=Depends(oauth2_scheme), db=Depends(get_db))`：
  解析令牌 → 取 `user_id` → 查 `User` → 检查 `status` → 返回用户
- **照抄视频会踩的 6 个坑，已适配并写进逐行中文注释**：
  1. `from backend.app.database import ...` → `from app.database import ...`
     （本项目源码根就是 backend，没有 `backend` 这个包）
  2. `from backend.app.utils.jwt import ...` → `from app.utils.jwt import ...`
  3. 视频调用了 `decode_access_token`，本项目 `utils/jwt.py` 原来只有
     `create_access_token`，直接照抄会立刻报红线 → 在该文件**末尾追加**
     `decode_access_token(token)`（`jwt.decode` 验签 + 自动检查 `exp`）
  4. 图二用了 `User` 却没导入 → 补 `from app.model.user import User`
  5. 视频 `tokenUrl="/api/authr/login"` 多了一个 `r`，改成项目实际 `/api/auth/login`
  6. 视频没判断用户不存在、也没写 `return` → 补 `if not user` 返回 401、
     补 `return user`，否则 `user.status` 会变成 500、依赖注入拿到的是 `None`
- **验证**（项目 `.venv` 实测）：`decode_access_token` 解出 `{'user_id': 1, 'exp': ...}`；
  `get_current_user(有效token)` 返回 `admin`（id=1，status=1）；
  无效 token → `401 登录已失效，请重新登录`；
  Pyright CLI 检查新文件 `errorCount 0 / warningCount 0`

**结果**：业务接口以后写 `Depends(get_current_user)` 就能要求登录并拿到当前用户；
下一步可把它挂到具体接口上，或把前端登录改成真实请求。

---

### 第 21 步：新增 `api/user.py` 用户信息接口 + 汇总路由（附 `main.py` 对比结论）

- 按教学视频三张截图：图一是 `api/__init__.py` 的汇总路由配置，图二是
  `api/user.py` 的代码，图三是视频版 `main.py`（只用于对比，见文末结论）
- 新建 `app/api/user.py`：`GET /api/user/info`，用
  `current_user: User = Depends(get_current_user)` 要求登录，返回
  `{"code": 200, "message": "请求成功", "data": UserResponse.model_validate(current_user)}`
- `app/api/__init__.py` **保留原有手写注释**，只在末尾追加图一配置：
  `api = APIRouter(prefix="/api")` → `include_router(auth_router)` + `include_router(user_router)`；
  `app/main.py` 相应改成 `from app.api import api` + `app.include_router(api)`（与图三写法一致）
- **照抄视频会踩的 5 个坑，已适配并写进逐行注释**：
  1. 视频 `app.models.user`（复数）→ 本项目是 `app.model.user`（单数）
  2. 视频 `backend.app.schemas.user` → `app.schemas.user`（本项目没有 backend 包）
  3. 图一第 2 行写 `from app.api.auth import router`，第 7 行却用 `auth_router`
     （截图被浮动工具栏挡住了别名）→ 补 `as auth_router`，否则 `NameError`
  4. **前缀重复**：本项目 `auth.py` 原来写 `prefix="/api/auth"`，再经总路由 `/api`
     会变成 `/api/api/auth/login` → 把子路由前缀改成 `/auth`，
     最终对外地址仍是 `POST /api/auth/login`，前端无需改动
  5. `UserResponse` 字段叫 `name`，数据库 `User` 里叫 `real_name`，
     直接 `model_validate(orm_user)` 会 `ValidationError` → 给 `name` 加
     `Field(validation_alias="real_name")` + `populate_by_name=True`，
     既让视频那行代码可用，又不破坏 `auth.py` 原有的 `UserResponse(name=...)` 构造
- **验证**（直接走 ASGI 层发真实请求；`TestClient` 需要 `httpx2`，本项目没装，
  为了验证不新增依赖）：路由 `/`、`/api/auth/login`、`/api/user/info`、`/health` 全部注册；
  `POST /api/auth/login` → 200 且 `data.name=系统管理员`；
  `GET /api/user/info` 不带 token → 401 `Not authenticated`、带 token → 200
  （返回不含密码的 5 个字段）、错误 token → 401「登录已失效，请重新登录」；
  `/` 与 `/health` → 200；Pyright 检查 4 个改动文件 `errorCount 0 / warningCount 0`
- **第二问：现有 `app/main.py` 与图三是否一样 → 不一样**，但核心骨架相同
  （`FastAPI()` + `app.include_router(api)` + `@app.get("/")`）。
  本项目版多出 `lifespan` 建表、CORS 白名单、`.env` 配置化标题、
  `/health` 依赖与数据库检查、根路径入口清单、`uvicorn` 自启动块；
  视频用模块级 `Base.metadata.create_all(bind=engine)` 直接建表、导入 `app.models.user`。
  **不建议改成视频的 14 行简化版**：会丢掉 CORS（前端 5173 跨域会失败）、
  建表失败兜底和健康检查

**结果**：`GET /api/user/info` 可用；以后新增业务模块只需在 `app/api/__init__.py`
里 include 一次，主应用不用再改。

---

### 第 22 步：创建 `common/` 统一响应与全局异常处理

> 按教学视频截图创建 `common/`（位于 `backend/` 根目录，与 `app/` 平级，不是 `app/common/`）。
> 作用是把「接口返回什么格式」「出错时返回什么格式」统一收口，避免每个接口各写各的。

- `common/__init__.py`：包标记，让 `common` 成为正式 Python 包
- `common/response.py`：统一响应信封 `Response(BaseModel)`，三个字段
  - `code: int`（业务状态码，成功 200 / 失败按情况）、`message: str`、`data: Any = None`
  - 两个类方法：`Response.success(message="请求成功", data=None)`（固定 code=200）、
    `Response.error(code=500, message="请求失败")`
  - 以后所有接口成功都返回 `Response.success(...)`，失败返回 `Response.error(...)`，
    前端拿到的永远是 `{code, message, data}` 这一种结构
- `common/exceptions.py`：自定义业务异常 + 4 个全局异常处理器（都是 `async` 函数，
  统一用 `JSONResponse(status_code=..., content=Response.error(...).model_dump())` 回包）
  - `BusinessException(Exception)`：带 `message` / `code`，构造函数 `super().__init__(message)` 用位置参数（Python 的 `Exception` 不收关键字 `message=`）
  - `business_exception_handler`：捕获 `BusinessException` → 用它的 code/message 回包
  - `http_exception_handler`：捕获 FastAPI 的 `HTTPException` → 用其 status_code/detail 回包
  - `validation_exception_handler`：捕获 `RequestValidationError`（参数校验失败）→ 固定 422「请求参数校验失败」
  - `global_exception_handler`：兜底捕获其它所有 `Exception` → 500「服务器内部错误，请联系管理员」
  - **照抄视频会踩的笔误，已修正并写进逐行注释**：
    函数名 `business_exception_hadler` → `business_exception_handler`；
    `from common.exception import HTTPException`（模块名错）→ 从 `fastapi` 导入；
    `from app.common.response import Response`（路径错）→ `from common.response import Response`；
    处理器第二参数统一写 `exc: Exception` + `assert isinstance(exc, 具体类型)` 以满足 Pyright 类型检查

**结果**：统一的「成功 / 失败」返回格式与异常兜底就绪；验证用 `raise BusinessException("用户名已存在", code=400)`
能被处理器捕获并返回 `{"code":400,"message":"用户名已存在","data":null}`；Pyright 检查 0 错误 0 警告。
（下一步：把这些处理器真正挂到主应用上才会生效。）

---

### 第 23 步：注册全局异常处理器到主应用

- 新建 `app/utils/main.py`：写 `register_exception_handlers(app)`，里面 4 行注册
  （`BusinessException` / `HTTPException` / `RequestValidationError` / `Exception`），
  **`Exception` 这行必须放最后**，否则会盖掉前面更具体的处理器
- 在 `app/main.py`：`include_router(api)` 之后导入并调用
  `from app.utils.main import register_exception_handlers` → `register_exception_handlers(app)`
  （注册代码现位于 `app/main.py` 第 35 行导入、第 75 行调用）

**结果**：4 类异常处理器全部生效；实测参数缺失的登录请求返回
`{"code":422,"message":"请求参数校验失败","data":null}`（统一信封已工作）。

---

### 第 24 步：登录响应统一改用 `Response.success` 信封（修掉 `auth.py` 损坏段 + 重启验证）

- 原 `app/api/auth.py` 登录返回段被写坏：误用了一个**本项目不存在的类**
  `LoginResponse.model_validate(user)`，还残留一段重复的死代码 `return {...access_token...}`；
  旧 uvicorn worker 因此卡在脏代码，一登录就 500
- 重写 `app/api/auth.py` 登录接口，去掉坏代码与死代码，登录成功统一返回：
  ```python
  return Response.success(
      message="登录成功",
      data={
          "token": token,                                  # create_access_token(user.id) 签发
          "user": UserResponse.model_validate(user).model_dump(),  # 直接读 ORM 对象
      },
  )
  ```
  （`UserResponse` 已配 `from_attributes=True` + `validation_alias="real_name"`，
  可直接从数据库 ORM 对象取字段，无需手写字段映射）
- **与第 17 步的关系**：第 17 步是「顶层 `access_token` + `token_type`」写法；
  这一步把登录结果也收进统一的 `Response.success` 信封，`data` 里仍带 `token` 与用户信息，
  前端取 `data.token` / `data.user` 即可，不再有顶层 `access_token` 字段
- 停掉卡在 SyntaxError 的旧后台服务，端口 8000 释放后重新启动干净的
  `uvicorn app.main:app --reload`（后台任务 `lnVnzo`）

**结果**：4 项验证全部通过 ——
① 正确登录 `admin/admin` → `code:200` + `data.token` + `data.user{id,name,email,phone,status}`；
② 错误密码 → `code:400`「账号或密码错误」（不签发 token）；
③ 空请求体 → `code:422`「请求参数校验失败」（全局异常处理器生效）；
④ 拿 token 调 `GET /api/user/info` → `code:200` + 用户数据（登录→鉴权全链路通）。
异常基础设施（`common/response.py` + `common/exceptions.py` + `app/utils/main.py` 注册）
与登录 / 鉴权接口全部跑通。

---

### 第 25 步：前端接入后端登录鉴权（对应视频第 1~5 步）

> 前端项目在 `cursor/frontend`（Vue 3 + Vite + Element Plus）。此前登录是前端 mock（写死 admin/admin，
> 未连后端）。这一步把它真正接到后端登录接口，形成完整登录鉴权闭环。共 5 个文件改动：

1. **新建 `src/utils/request.ts`（公共请求工具）**：`axios.create` 造统一 `request` 实例，
   `baseURL:'/api'`（自动加 `/api` 前缀）+ `timeout:10000`；请求拦截器从 `localStorage.getItem('token')`
   取 token 放进 `Authorization: Bearer <token>`；响应拦截器统一处理后端 `{code,message,data}` 信封
   （`code!==200` 弹 `message` 并 reject，成功返回 `body.data`）；401 清 token 跳 `/login`。
   以后前端调后端统一 `import request from '@/utils/request'`，不用每次写完整地址。
2. **改 `vite.config.ts` 加 `/api` 代理**：`server.proxy{ '/api' → http://127.0.0.1:8000 }`，
   前端发 `/api/xxx` 自动转发到后端 8000（后端路由本身带 `/api`，故【不改写路径】）。
3. **改 `src/views/LoginView.vue`（假登录→真登录）**：加 `import request from '@/utils/request'`；
   `handleLogin` 删掉写死的 admin/admin 判断，改 `request.post('/auth/login', {username,password})` 调后端；
   成功 `localStorage.setItem('token', data.token)` 存 token 并跳 `/home`；catch 不重复弹错、finally 复位 loading。
4. **改 `src/router/index.ts` 加登录守卫**：`router.beforeEach` —— 没 token 且去的不是 `/login` → 强制回 `/login`；
   有 token 且去 `/login` → 直接送 `/home`。没登录进不了受保护页、已登录进不了登录页，无死循环。
5. **改 `src/layouts/BasicLayout.vue` 退出登录**：`onCommand('logout')` 由清
   `sessionStorage.lab_logged_in` 改成 `localStorage.removeItem('token')`（清登录状态）再跳 `/login`。

**结果**：前端登录鉴权闭环打通 —— 登录存 token(localStorage) → 路由守卫按 token 放行/拦截 →
`request` 自动带 `Bearer token` 请求后端 → 退出清 token。端到端实测（走 Vite 代理）：
`POST /api/auth/login` 返 `code:200` + `data.token` + `data.user`；带 `Authorization: Bearer` 调
`GET /api/user/info` 返 `code:200` + 用户数据；前端 HMR 编译无错误。

---

### 第 26 步：用户注册接口（RegisterRequest + POST /api/auth/register）+ 加宽 password 列

- `app/schemas/auth.py`：在 `LoginRequest` 旁加 `RegisterRequest`（username / password / real_name 可空，不填姓名就用用户名）
- `app/api/auth.py`：import 增补 `RegisterRequest`、`hash_password`、`BusinessException`；
  新增 `POST /api/auth/register` —— 先查用户名占用（占用则 `raise BusinessException("用户名已存在", code=400)`），
  再建 `User`（`real_name or username`、`password=hash_password(...)` 哈希存、`role="student"`），
  `db.add/commit/refresh` 后 `Response.success(data=UserResponse.model_validate(user))` 返回用户信息（不带密码）
- **数据库改动（非破坏性加宽，不丢数据）**：`lab-agent.user` 表的 `password` 列原是 `varchar(50)`，
  装不下 bcrypt 60 字符哈希，注册时报 `DataError(1406, "Data too long for column 'password'")`。
  模型 `User.password` 早就是 `String(255)`，但 `create_all` 不会改已存在的表，故需手动 ALTER 加宽：

  ```sql
  ALTER TABLE `user` MODIFY `password` VARCHAR(255) NOT NULL COMMENT '密码';
  ```

- 验证：注册 testuser04 → `code:200` + `data{id,name,...}`（密码哈希存）；同名再注册 →
  `code:400`「用户名已存在」（BusinessException 处理器生效）；用 testuser04 登录 → `code:200` + token（bcrypt 可校验）

**结果**：注册接口可用、密码哈希存储；配合登录 / 路由守卫 / 退出登录，用户体系完整闭环。

---

### 第 27 步：前端注册页面三件套（RegisterView.vue + 路由 + 登录页「去注册」入口）

- `frontend/src/views/RegisterView.vue`（新增）：`<script setup lang="ts">` 注册页，
  用户名 / 密码 / 确认密码 / 姓名（选填）四个字段，页面风格完全复用登录页
  （bg-layer 背景装饰 + 品牌栏 + 居中卡片 + 渐变按钮 + 双媒体查询自适应）；
  前端校验用户名密码非空、两次密码一致，通过后调 `request.post('/auth/register', { username, password, real_name })`
  （real_name 不填传空串，后端用用户名兜底），成功提示「注册成功，请登录」并跳 `/login`；
  失败不重复弹错（拦截器统一弹）；卡片底部「已有账号？去登录」链接跳回登录页
- `frontend/src/router/index.ts`：`/login` 旁新增 `/register` 路由（懒加载 RegisterView，
  `meta: { title: '注册', fullTitle: '智能预约系统' }`）；
  路由守卫白名单改为 `['/login', '/register']`（未登录也能进注册页），
  已登录访问 `/login` 或 `/register` 一律重定向 `/home`
- `frontend/src/views/LoginView.vue`：登录按钮下方加「没有账号？**去注册**」链接 → `/register`
  （`.to-login` + `.link-btn` 样式，与注册页底部链接对称），并补小屏 `@media` 间距
- 验证：Vite HMR 无报错、`/src/views/RegisterView.vue` 模块编译 200；
  走代理 `POST /api/auth/register` 建 testuser05 → `code:200` + `data{id,name:"注册测试"}`，
  再用 testuser05 登录 → `code:200` + token

**结果**：注册 → 登录 → 进首页 完整闭环可用，登录 / 注册两页互通跳转。

---

### 第 28 步：文件上传功能（save_upload + POST /api/upload + /uploads 静态访问）

- `app/config.py`：Settings 新增「四、文件上传配置」—— `UPLOAD_DIR`（默认 `backend/uploads` 绝对路径，
  不依赖启动目录）、`MAX_UPLOAD_SIZE_MB=5`、`ALLOWED_EXTENSIONS="jpg,jpeg,png,gif,webp"`
- `app/utils/file.py`（新增）：`async save_upload(file, category="common") -> {url, filename, size}`
  - category 只允许 `[A-Za-z0-9_-]{1,32}`（防 `../../` 路径穿越），不合法抛 `BusinessException(code=400)`
  - 只取原文件名扩展名做白名单校验，非法 → `BusinessException("不支持的文件类型", code=400)`
  - 保存到 `uploads/<分类>/<年>/<月>/<日>/<uuid4().hex>.<ext>`：uuid 重命名，同名不覆盖、原名不进路径
  - 每块 1MB 分块读写统计大小，超 5MB 删文件并抛 `BusinessException("文件不能超过 5MB")`
    （Windows 删不掉已打开文件：先关句柄再删）；写盘中途出错也清半截文件
  - 返回相对 URL 形如 `/uploads/avatar/2026/11/05/xxx.png`（`os.sep` 统一换 `/`）
- `app/api/upload.py`（新增）：`router = APIRouter(prefix="/upload", tags=["文件上传"])`，
  `POST /api/upload`（路径写 `""` 拼前缀）收 `file: UploadFile = File(...)` + `category: str = Form("common")`，
  `Depends(get_current_user)` 要求登录，成功 `Response.success(message="上传成功", data=info)`
- 接线：`app/api/__init__.py` 注册 upload_router；`app/main.py` 启动时
  `os.makedirs(settings.UPLOAD_DIR, exist_ok=True)` + `app.mount("/uploads", StaticFiles(...))`
- 配套：`backend/.gitignore` 加 `uploads/`；`vite.config.ts` 的 proxy 加
  `'/uploads' → http://127.0.0.1:8000`（前端 `<img src="/uploads/...">` 直接显示）
- 验收 6 条全过：① 无 token→HTTP 401 ② png→code:200 + `/uploads/avatar/2026/11/05/<uuid>.png` + 磁盘存在
  ③ .exe→code:400「不支持的文件类型」④ 6MB→code:400「文件不能超过 5MB」（无残留文件）
  ⑤ `/uploads/...` 直连 8000 和走 Vite 代理都返回 200 image/png ⑥ 同名文件传两次 → 两个不同 uuid 文件互不覆盖

**结果**：登录用户可上传图片，落盘、校验、静态访问全链路可用。

---

### 第 29 步：个人信息页（GET/PUT /api/user/info + ProfileView.vue）

- `app/schemas/user.py`：`UserResponse` 增加 `username` / `role` / `avatar` 三字段
  （账号、角色、头像，前端个人信息页展示用）；新增 `UpdateUserRequest`
  （`name` / `email` / `phone` / `avatar` 全可选，只改传的部分）
- `app/api/user.py`：把 `get_user_info` 的返回也统一成 `Response.success`；
  新增 `PUT /api/user/info`（拼前缀后完整路径 `PUT /api/user/info`）：
  校验登录（`Depends(get_current_user)`），`name` 为空字符串 → `Response.error(code=400,"名称不能为空")`，
  否则把改动写进 `real_name` / `email` / `phone` / `avatar` 并 `db.commit()`，返回 `Response.success("更新成功", data=最新UserResponse)`
- 顺带修一个真 bug：`user.avatar` 列原是 `VARCHAR(50)`，但头像 URL
  `/uploads/avatar/2026/11/05/<uuid>.png` 有 60+ 字符，写入直接 500；
  已用 `ALTER TABLE `user` MODIFY `avatar` VARCHAR(255)` 加宽，并同步 `app/model/user.py`
- 前端：`src/views/ProfileView.vue`（新增），按设计稿还原：头像（可点击上传，走 `POST /upload` + `category=avatar`）、
  账号/角色用 `disabled` 只读、名称/邮箱/手机号可编辑，「保存修改」按钮 → `PUT /user/info`；
  进入页面 `GET /user/info` 预填，保存成功 `ElMessage.success("更新成功")`
- 接线：`src/router/index.ts` 在 BasicLayout 子路由加 `/profile`（`meta:{title:'个人信息'}`）；
  `src/layouts/BasicLayout.vue` 右上「个人中心」下拉项 `command==='profile'` → `router.push('/profile')`
- 验收：① 无 token 调 `GET /api/user/info` → HTTP 401 ② 带 token → 200 且返回 username/name/role/email/phone/avatar
  ③ `PUT` 空名称 → code:400「名称不能为空」④ `PUT` 改邮箱/手机号 → code:200「更新成功」并回写
  ⑤ 上传头像 → 落 `uploads/avatar/...` 且 `PUT` 写入 avatar 后回读一致、直连 `/uploads/...` 返回 200 image/png

**结果**：「个人中心」可看可改自己的账号信息、可换头像，改动实时落库。

---

### 第 30 步：用户状态单数据源重构（store + 头部/个人中心同步）

- 新建 `frontend/src/stores/user.ts`：用 Vue `reactive` 建唯一 `userState`
  （id/username/name/role/email/phone/avatar）；`setUser(data)` 整体写入、`updateUser(patch)` 局部更新、
  `clearUser()` 退出、`userInitial()` 取姓名首字；三处写入/更新都 `localStorage('user')` 持久化，
  模块加载即 `restore()` 从本地恢复（刷新/重进不丢）；`clearUser` 同时清 token
- `LoginView.vue`：登录成功 `setUser(data.user)`（后端 data.user 含全部字段），与 token 一起入库
- `BasicLayout.vue`：删掉写死的「管理员 / admin@lab.edu.cn / 管」；
  头部头像 `<img :src="userState.avatar">`（无则姓名首字圆形色块），姓名/邮箱取 `userState.name/email`；
  信息块 `max-width:160px` + `min-width:0` + `ellipsis`（超长不换行/不撑破）；头像固定 36px `flex-shrink:0`；
  登出改调 `clearUser()`；「个人中心」下拉 → `/profile`
- `ProfileView.vue`：全部改读 `userState`（头像同步头部）；进入页 `GET /user/info` → `setUser` 预填；
  上传头像成功 `updateUser({avatar})` 头部立即变；保存资料 `updateUser({name,email,phone})`；
  布局收敛：`max-width:720px margin:0 auto`、`grid(88px 1fr)` 表单、输入框 `width:100%`、`avatar` 区收到 88px；
  `<900px` 隐藏邮箱行，只留头像+姓名
- 验收（设计层已满足）：① 改头像/资料后右上角即时同步 ② 刷新/重登从 localStorage 恢复
  ③ 超长用户名/邮箱省略号不破版 ④ 多账号切换各自正确 ⑤ <900px 不错乱 ⑥ 无头像显首字色块不破图

**结果**：全站用户信息只有 store 一份，头部与个人中心实时一致，长文本/多账号/小窗口都健壮。

---

### 第 31 步：实验室 / 设备 / 预约 三大业务功能（后端 + 前端）

#### 数据模型（新建，均在 app/model/）
- `lab.py`：`Lab`（name 非空 / code 非空且 unique / location / capacity / description / status 默认1）
- `device.py`：`Device`（lab_id 外键非空 / name 非空 / code 非空且 unique / model / status 默认1 / description）
- `appointment.py`：`Appointment`（user_id、lab_id 外键非空 / device_id 外键可空 / appoint_date Date / start_time、end_time Time / purpose / status 默认0）
- `app/database.py` 的 `init_db()` 内导入三个模型 → `create_all` 自动建表（已验证三张表存在）

#### 公共依赖 + schemas
- `app/dependencies/permission.py`：`require_admin(current_user=Depends(get_current_user))`，role!=admin 抛 HTTPException(403)；学生接口只用 `get_current_user`
- `app/schemas/lab.py`：`LabResponse / LabCreate / LabUpdate`
- `app/schemas/device.py`：`DeviceResponse`（带 lab_name）/ `DeviceCreate / DeviceUpdate`
- `app/schemas/appointment.py`：`AppointmentResponse`（带 lab_name/device_name/user_name）/ `AppointmentCreate / AppointmentReview`

#### 后端接口（均挂 /api 前缀，全部逐行中文注释）
- `app/api/lab.py`（管理员）：`/lab/list`(分页+keyword+status) `/lab/options`(启用下拉) `/lab/{id}`(404) `POST /lab`(code 唯一→400「实验室编号已存在」) `PUT /lab/{id}`(排除自身唯一) `DELETE /lab/{id}`(有设备→400「请先移除该实验室下的设备」)
- `app/api/device.py`（管理员）：`/device/list`(lab_id+keyword+status，带 lab_name) `/device/{id}` `/device`(校验 lab 存在+code 唯一) `PUT /device/{id}` `DELETE /device/{id}`(有未完成预约→400)
- `app/api/appointment.py`：学生端 `lab_public_router`(`/lab/available` 启用实验室+device_count、`/lab/{id}/devices`) + `router`(`POST /appointment` 校验过去日期/时间、start<end、同实验室或同设备时间段重叠排除已取消/拒绝、`status=0`；`GET /appointment/my` 分页；`PUT /appointment/{id}/cancel` 仅本人且 0/1)；管理员端 `GET /appointment/list` 分页、`PUT /appointment/{id}/review` 仅待审核、status∈{1,2}

#### 路由注册（app/api/__init__.py）
- **顺序关键**：`lab_public_router` 必须排在 `lab_router` 之前，否则 `/lab/available` 会被 admin 的 `/lab/{id}` 抢先匹配导致学生 403（已踩坑并修复）
- 依次 include：lab_public_router → lab_router → device_router → appointment_router → 原有 auth/user/upload

#### 前端（Vue3 + Element Plus，复用 request/store）
- 路由 `src/router/index.ts`：/laboratory、/device、/appointment、/user、/profile、/student/labs、/student/my-appointments 全部挂 BasicLayout 子路由；管理员路由 `meta.role='admin'`；守卫新增「学生访问 admin 路由→跳 /student/labs」
- 菜单 `src/layouts/BasicLayout.vue`：按 `userState.role` 动态渲染（管理员：首页/实验室管理/设备列表/预约审核/用户管理；学生：首页/实验室列表/我的预约）
- 新建 5 个页面（均 `<script setup lang="ts">`、loading/分页/el-dialog/form 校验/ElMessageBox 二次确认/el-tag 状态色）：
  - `LabManageView.vue`（/laboratory）：工具栏(关键字+状态+新增)、表格(编号/名称/位置/容量/状态/操作)、增改 dialog、删除确认
  - `DeviceManageView.vue`（/device）：工具栏(实验室下拉+关键字+状态+新增)、表格(编号/名称/所属实验室/型号/状态/操作)、dialog 实验室下拉、删除确认
  - `AppointmentReviewView.vue`（/appointment）：状态筛选、表格(实验室/设备/预约人/日期/时间段/用途/状态/操作)、待审核行「通过/拒绝」(拒绝可填原因)
  - `StudentLabsView.vue`（/student/labs）：实验室卡片网格(名称/位置/容量/设备数/状态)、点击「预约」弹窗(日期禁过去、起止时间、设备下拉、用途)→ POST /appointment
  - `StudentMyAppointmentsView.vue`（/student/my-appointments）：表格(实验室/设备/日期/时间段/用途/状态/操作)、取消二次确认
- 修复：所有列表「全部」状态(lab_id)筛选为空时**不传该参数**，否则空串触发后端 422

#### 验收（全部实测通过）
1. 管理员实验室/设备增删改查 + 分页/搜索/筛选生效
2. 重复编号 → code:400「编号已存在」
3. 删有设备的实验室→400「请先移除该实验室下的设备」；删有未完成预约的设备→400
4. 学生看实验室列表/设备列表、成功提交预约
5. 时间段重叠 → code:400「该时间段与已有预约冲突，请更换时间」
6. 过去日期/时间 → code:400
7. 无 token→401；学生调管理员接口→403
8. 管理员审核通过/拒绝、学生看到状态变化并可取消（状态机 0→1/2；0/1→3）

**结果**：三大业务闭环可用，前后端通过 Vite 代理实测打通。

---

### 第 32 步：设备列表管理页改造（还原截图样式）+ 内置示例数据（seed）

#### 需求
把「设备列表管理」页做成指定截图样式，并在**首次启动且表为空时**内置与截图一致的 4 个实验室 + 8 台设备。

#### 数据模型（app/model/device.py）
- **去掉** `code`（设备编号）列；**新增** `image`（String255，可空，图片 URL）、`quantity`（Integer，默认 1）
- `status` 语义改为 **1=正常 / 0=维修**（原 1可用/2维修中/0报废 不再使用；`appointment.py` 里 `device.status != 1` 视为不可用，正好对应「维修不可用」）
- `lab` 表保持不变（仍含 code/description，实验室下拉只返回 id+name）

#### schemas（app/schemas/device.py）
- `DeviceResponse`：去 `code`，加 `image` / `quantity`，保留 `lab_name`
- `DeviceCreate / DeviceUpdate`：`quantity` 用 `Field(ge=1)` 限制至少 1；`status` 用 `Field(ge=0, le=1)` 限制只能 0/1

#### 后端接口（app/api/device.py，均管理员权限）
- `/device/list`：关键字只匹配 `name`（去掉 `code` 模糊）；`lab_id` / `name` / `status` 筛选；返回带 `lab_name`，分页 `{list,total}`
- `POST /device`、`PUT /device/{id}`：去掉「编号唯一」校验，写入 `image` / `quantity`；其余（校验 lab 存在、删除查未完成预约）不变

#### 示例数据（app/seed.py，新增 + main.py 接入）
- `seed_data()`：**仅当 `Lab` 或 `Device` 表为空时才插入**，重复启动不会重复写入（幂等）
- 实验室 4 个：软件工程实验室(实验楼A-301,60)、机器人实验室(实验楼B-205,40)、人工智能实验室(实验楼A-402,45)、网络工程实验室(实验楼C-101,50)，状态均启用
- 设备 8 台：软件工程实验室 4 台（代码服务器/控制仪/显示器/开发主机）、机器人实验室 4 台（Jetson Orin/RealSense 深度相机/Livex 激光雷达/UR5 机械臂），`image` 留空、`status=1`
- 接入：`app/main.py` 的 `lifespan` 在 `init_db()` 之后调用 `seed_data()`

#### 一次性迁移（已执行，仅一次）
- `ALTER TABLE device DROP COLUMN code; ADD COLUMN image VARCHAR(255) NULL; ADD COLUMN quantity INT NOT NULL DEFAULT 1;`
  （`create_all` 不能删列，必须手动迁移）
- 清空此前测试残留的 `appointment / device / lab` 行（顺序：先删有外键依赖的预约，再设备，最后实验室），让 seed 能以空表写入演示数据
- 注意：这次清空了旧的测试数据，仅因它们会阻断「表为空才插入」的 seed；正式环境首次部署本就是空表，无需此步

#### 前端（src/views/DeviceManageView.vue 重写）
- 工具栏 4 项（按截图）：`el-input`(placeholder「请输入名称查询」,200px) + `el-select`(实验室下拉,180px,可清空,来自 `/lab/options`) + `查询`(primary+Search 图标) + `新增`(success+Plus 图标)
- 表格 7 列（stripe/border/empty-text「暂无数据」/loading）：所属实验室、设备名称(show-overflow-tooltip 省略号)、图片(`el-image` 56×40 cover 圆角 + 点击预览；`image` 为空显示灰色占位块带 Picture 图标)、型号规格、数量、状态(`el-tag` 正常绿/维修橙)、操作(编辑蓝/删除红)
- 弹窗 7 字段（顺序同截图）：所属实验室*(select)、设备名称*(input)、说明(textarea)、图片(点击上传)、型号规格(input)、数量*(`el-input-number` :min=1)、状态(`el-radio` 正常/维修)；底部 取消/确定(loading)
- **图片上传复用 `POST /api/upload`**：用隐藏 `<input type=file>` + `FormData` + `request.post('/upload', fd)`（拦截器自动带 token），category=device，返回 `data.url` 直接回填 `form.image`；无图显示占位、有图可更换/移除
- 校验：所属实验室、设备名称、数量必填；查询/回车重置到第 1 页；删除二次确认；成功提示后关弹窗并刷新

#### 验收（全部实测通过）
1. 首启列表含 8 台示例设备（软件工程 4 + 机器人 4），实验室下拉 4 个
2. 名称模糊查询、实验室筛选生效（空值不传参，避免 422）
3. 新增时数量=0 → 422、status=2 → 422（后端校验）
4. 图片列空显示占位图、上传后显示缩略图且可预览
5. 状态保存后显示「正常/维修」且颜色正确
6. 编辑回填、删除二次确认正常
7. 重复启动不重复插入（表非空即跳过 seed）

**结果**：设备页外观与截图一致，并内置可演示的示例数据；前后端经 Vite 代理实测打通。

---

### 第 33 步：账号管理模块（仅管理员，只读查看）

#### 后端（在现有 user 路由下新增，`app/schemas/user.py` + `app/api/user.py`）
- `AccountResponse`（新增响应模型）：id / username / name(别名映射 real_name) / role / email / phone / avatar / status / create_time(datetime)；
  **不定义 password 字段 → model_validate 只挑声明过的字段，密码绝不会随接口返回**
- `GET /api/user/list`（`Depends(require_admin)`）：分页 page/page_size（10~100）；筛选 keyword（username 或 real_name 模糊，or_）/ role（admin|student 字符串）/ status（1|0）；按 id 升序；返回 `{list, total}`
- `GET /api/user/detail/{user_id}`（`Depends(require_admin)`）：不存在 → 404「账号不存在」
- **路径注意**：用 `/user/list` 和 `/user/detail/{id}`，不用 `/user/{id}`，避免与已有 `/user/info` 产生路由歧义
- 顶部 import 补：`Query`（fastapi）、`or_`（sqlalchemy）、`require_admin`、`AccountResponse`

#### 前端
- 路由 `src/router/index.ts`：**删除原 `/user`「用户管理」占位页（EmptyModuleView）**，新增 `/accounts` → `AccountsView.vue`，`meta:{title:'账号管理', role:'admin'}`（学生访问会被守卫重定向到 /student/labs）
- 菜单 `src/layouts/BasicLayout.vue`：adminMenus 里「用户管理」→「账号管理」(path:/accounts, icon:User)，学生菜单不变（学生看不到该入口）
- 新建 `src/views/AccountsView.vue`（只读，与设备页同套卡片样式）：
  - 工具栏：el-input「搜索账号/姓名」(200px, 回车/清空触发) + 角色下拉(全部/管理员/学生) + 状态下拉(全部/启用/禁用) + 查询(primary+Search) + 重置(RefreshLeft，清空全部条件回第 1 页)
  - 表格 8 列：账号、姓名（均 show-overflow-tooltip 省略号）、角色(el-tag 管理员蓝/学生绿)、邮箱、手机号（空显示 "-"）、状态(el-tag 启用绿/禁用红)、创建时间(ISO 转 `YYYY-MM-DD HH:mm`)、操作(「查看」)
  - 分页 `layout="total, sizes, prev, pager, next"`（即「共 X 条」），空数据显示「暂无数据」，loading
  - 「查看」→ `GET /user/detail/{id}` 弹只读 `el-dialog`：头像（无图用姓名首字圆形色块兜底）+ `el-descriptions` 单列展示账号/姓名/角色/邮箱/手机号/状态/创建时间，**无密码、无编辑按钮**（启用/禁用本期不做）
  - 筛选「全部」时**不传该参数**（沿用既有防 422 约定）

#### 验收（全部实测通过）
1. 管理员列表 200，返回 5 个账号（admin/student01/student02/彭新/stutest），逐条核对字段齐全且 **password 不存在**
2. keyword=student → 2 条；role=admin → 1 条；status=1 → 5 条
3. detail/1 → 字段 = avatar/create_time/email/id/name/phone/role/status/username，无 password；detail/999 → 404
4. 学生 token 调 list 与 detail 均 **403**；无 token → **401**
5. 前端三模块（AccountsView/router/BasicLayout）Vite 编译均 200；经 Vite 代理调 /api/user/list → 200 total=5
6. grep 确认前端无残留 `/user` 路由引用（只剩 /user/list、/user/detail、/user/info 等 API 调用）

**结果**：管理员可在左侧「账号管理」分页查看全部账号并点「查看」看详情；学生前后端双重拦截（菜单不可见 + 接口 403 + 路由守卫重定向）。

---

### 第 34 步：引入 service 分层（示范迁移 appointment 预约模块）

#### 分层规范（所有新代码必须遵守，写进 app/services/__init__.py 头注释）
1. 目录 `app/services/`，每个业务模块一个 `*_service.py`
2. service 函数第一个参数固定 `db: Session`（**定时任务除外**，用 `SessionLocal` 自己开会话）
3. 业务错误一律 `BusinessException(message="...", code=400)`，**不抛 HTTPException**（HTTP 语义留给框架层）
4. 数据库写入（add / commit / refresh）在 service 里完成
5. api 层只做：接收参数 → 调 service → `return Response.success(...)`
6. service 返回 ORM 对象或 dict/list，由 api 层转成 schema
7. 命名：`create_xxx / list_xxx / get_xxx / update_xxx / delete_xxx / 业务名`（如 `audit_reservation`）

#### 渐进策略
- 只示范迁移 appointment（业务规则最多）；auth / user / lab / device **保持原样能跑**
- 今后新功能直接写 service；老模块等下次要改时再顺手迁移
- 学生端「浏览实验室/设备」两个只读查询暂留 api/appointment.py（属 lab 域，迁 lab 时再挪）

#### 新建文件
- `app/services/__init__.py`：包标记 + 分层规范注释
- `app/services/appointment_service.py`（逐行中文注释）：
  - 状态常量 `STATUS_PENDING/APPROVED/REJECTED/CANCELLED/ENDED(4 新增)`
  - `build_appointment_data(db, a)`：拼 实验室/设备/学生 名称的响应字典
  - `create_reservation(db, user_id, lab_id, device_id, appoint_date, start_time, end_time, purpose) -> dict`：过去时间 / 顺序 / 实验室启用 / 设备归属 / 时段冲突 全套校验 + 写入
  - `list_my_reservations(db, user_id, page, page_size, status) -> (list[dict], total)`
  - `cancel_reservation(db, reservation_id, user_id) -> dict`：仅本人、仅 0/1 可取消 → 3
  - `list_all_reservations(db, page, page_size, status) -> (list[dict], total)`
  - `audit_reservation(db, reservation_id, status) -> dict`：仅待审核可审，结果只能 1/2
  - `exp_end_pending_reservations() -> int`：**定时任务**，SessionLocal 自开会话，把结束时刻已过、仍处于 0/1 的预约自动置为 **4=已结束**，返回条数
- `app/main.py`：lifespan 在 seed 之后调用一次 `exp_end_pending_reservations()`（启动顺手清一次 + 打日志；以后接 APScheduler 等调度框架时挂同一个函数即可）

#### api/appointment.py 薄化
- 5 个预约端点全部改成「调 service + `Response.success`」；**路径 / 请求体 / 返回格式 / 提示文案（预约提交成功等待审核 / 已取消 / 审核完成）一律不变**，前端零改动
- 「预约不存在」由原 `HTTPException(404)` 改为 `BusinessException(code=404)`：HTTP 状态 404→200，但 body 仍是 `{code:404, message:"预约不存在"}`，前端拦截器按 code 弹错，**用户体验不变**（老接口如需严格 HTTP 404 可保留 HTTPException，但 service 层规范统一用 BusinessException）

#### 前端小改（配合状态 4）
- `AppointmentReviewView.vue` / `StudentMyAppointmentsView.vue`：`appointmentStatusMeta` 补 `4=已结束(灰)`，筛选下拉加「已结束」选项，避免定时任务产生的状态 4 落到「已取消」兜底

#### 回归测试（全部实测通过）
1. 学生浏览 /lab/available、/lab/{id}/devices → 200（路由顺序与行为未变）
2. 提交预约 → 200「预约提交成功，等待审核」status=0，lab_name/user_name 正常关联
3. 同时段再约 → 400 冲突；过去日期 → 400；开始≥结束 → 400
4. 跨用户取消 → 400「只能取消自己的预约」
5. 审核通过 → 「审核完成」status=1；重复审核 → 400；对不存在 id 审核 status=5 → code=404「预约不存在」（校验顺序与迁移前一致：先查存在再查状态）
6. 本人取消 → 「已取消」status=3；再取消 → 400
7. 取消不存在 id=99999 → HTTP 200 + code=404「预约不存在」（BusinessException 版，前端照常弹错）
8. 学生调 /appointment/list → 403；无 token → 401；学生 /my、管理员 /list 正常
9. 定时任务实测：插入一条昨天 10-12 点、状态 1 的预约 → `exp_end_pending_reservations()` 返回 1 → **新开会话**查询状态已置 4 → 测试数据已清理（用户彭新的预约保留未动）
10. 前端两个改动页面 Vite 编译 200

**坑**：验证定时任务时用同一个会话 `refresh` 看不到另一会话提交的变更（MySQL 可重复读快照），必须**换一个全新 SessionLocal 再查**才能确认。

**结果**：service 分层落地，预约模块 5 个端点行为与迁移前完全一致；今后新功能一律先写 service。

---

## 二、项目结构

```
backend/
├── .env                     ① 配置文件（含数据库连接串、API 配置）
├── .env.example            ② .env 模板（不含真实密码，可提交）
├── main.py                 ③ 兼容入口（薄包装层，转发到 app/main.py）
├── requirements.txt        ④ 依赖清单
├── README.md               ⑤ 环境搭建与使用说明
├── DEVELOPMENT.md          ⑥ 本文档（唯一开发路线记录）
├── .venv/                   Python 虚拟环境（不提交）
└── app/
    ├── __init__.py
    ├── main.py             ⑦ FastAPI 主应用：建表、CORS、注册路由、/health
    ├── config.py           ⑧ 读 .env
    ├── database.py         ⑨ 连数据库
    ├── model/
    │   ├── __init__.py
    │   └── user.py         ⑩ 用户表
    ├── schemas/
    │   ├── __init__.py
    │   ├── auth.py         ⑪ 登录请求模板
    │   └── user.py         ⑫ 用户响应模板
    ├── utils/
    │   ├── __init__.py
    │   └── jwt.py          ⑬ 生成 JWT token（create_access_token）
    └── api/
        ├── __init__.py
        └── auth.py         ⑭ 登录接口
```

## 三、模块职责

| 模块 | 职责 |
|---|---|
| `.env` | 配置中心，放 API 配置和数据库连接串，含密码不提交 |
| `app/config.py` | 读 `.env`，输出 `settings`；另提供 `JWT_*` 只读别名兼容教程命名 |
| `app/database.py` | 连数据库、提供会话、定义公共父类 Base、建表 |
| `app/model/user.py` | 定义用户表（决定数据怎么存） |
| `app/schemas/auth.py` | 定义登录请求格式（决定输入长什么样） |
| `app/schemas/user.py` | 定义用户响应格式（决定输出长什么样） |
| `app/utils/jwt.py` | `create_access_token(user_id)`：生成带过期时间的 JWT token |
| `app/api/auth.py` | 登录接口（决定具体怎么干），目前还没调用上面的工具函数 |
| `app/main.py` | **真正的入口**：启动建表、CORS、注册路由、健康检查 |
| `main.py` | 兼容旧命令的薄包装层，只转发 `app/main.py` 的 app 对象 |

## 四、模块交互

```
.env → config.py → database.py → model/user.py
                                      ↓
                                   api/auth.py ← schemas/auth.py（收数据）
                                      ↓          ← schemas/user.py（回数据）
                                   app/main.py（include_router 注册路由、启动）
                                      ↑
                                 main.py（兼容壳，转发同一个 app）

补充：config.py → utils/jwt.py（读密钥 / 算法 / 有效期签发 token）；
      api/auth.py → utils/jwt.py（登录成功后调用，待接入）
```

文字版：

1. `config.py` 读 `.env`，把 `DATABASE_URL` 给 `database.py`
2. `database.py` 连上 MySQL，给 `model/user.py` 提供父类 `Base`
3. `api/auth.py` 用 `database.get_db` 拿会话，用 `model.user.User` 查数据
4. `api/auth.py` 用 `schemas/auth.LoginRequest` 接收前端数据，用 `schemas/user.UserResponse` 返回数据
5. `app/main.py` 启动时调 `init_db()` 建表，并 `include_router` 注册 `api/auth.py` 的路由；
   根目录 `main.py` 只是转发，不写业务代码
6. 前端 → `app/main.py` → `api/auth.py` → `model/user.py` → MySQL；返回走 `schemas/user.py`
7. 启动命令：`uvicorn app.main:app --reload`（推荐）或 `uvicorn main:app --reload`（兼容）
8. `utils/jwt.py` 从 `config.py` 的 `JWT_*` 别名取密钥 / 算法 / 有效小时数，
   生成 token；下一步由 `api/auth.py` 在登录成功时调用它

---

## 五、结构更新（截至第 24 步，仅作补充，不改动上面各章节）

- `backend/` 根目录新增 `common/`（与 `app/` 平级，不是 `app/common/`），含：
  - `common/__init__.py`、`common/response.py`（统一响应信封 `Response`）、
    `common/exceptions.py`（业务异常 + 4 个全局处理器）—— 详见第 22 步
  - 注册关系：`common/exceptions.py` 的 4 个处理器，由 `app/utils/main.py`
    的 `register_exception_handlers(app)` 挂到主应用，并在 `app/main.py` 第 75 行调用 —— 详见第 23 步
- `app/utils/` 新增 `main.py`（`register_exception_handlers`）
- 登录接口 `app/api/auth.py` 现已统一返回 `Response.success(data={token, user})` —— 详见第 24 步
- 当前目录（简版）：

  ```
  backend/
  ├── common/            ← 新增：统一响应 + 全局异常
  │   ├── __init__.py
  │   ├── response.py    # Response 信封
  │   └── exceptions.py  # BusinessException + 4 处理器
  └── app/
      ├── main.py        # 第 35 行导入、第 75 行调用 register_exception_handlers
      ├── utils/
      │   ├── jwt.py
      │   └── main.py    ← 新增：register_exception_handlers(app)
      ├── api/
      │   ├── auth.py    # 登录已用 Response.success 信封
      │   └── user.py
      └── dependencies/auth.py
  ```