"""智能预约系统 · FastAPI 主应用（后端真正的入口）

职责：读取 .env 配置、启动时初始化数据库、注册所有业务路由、提供健康检查。
推荐启动命令（在 backend 目录下执行）：
    uvicorn app.main:app --reload
"""

# 从标准库导入 os：创建上传目录、判断路径用
import os

# 从标准库导入两个工具：import_module 动态导入包做依赖检查，metadata 读取包版本
from importlib import import_module, metadata

# 从标准库导入 python_version，用在健康检查里显示当前 Python 版本
from platform import python_version

# 从标准库导入 asynccontextmanager，用来定义「服务启动 / 关闭时要做的事」
from contextlib import asynccontextmanager

# 导入 FastAPI 主类和跨域中间件
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 导入 StaticFiles：把磁盘上的上传目录挂成静态文件服务，浏览器才能直接访问图片
from fastapi.staticfiles import StaticFiles

# 导入 SQLAlchemy 的 text：把普通字符串包成一条可执行 SQL（这里用 SELECT 1 测连通）
from sqlalchemy import text

# 导入 config.py 里的配置对象，它的值全部来自 .env
from app.config import settings

# 导入 database.py 里的数据库引擎和建表函数
from app.database import engine, init_db

# 导入 api 包里汇总好的「总路由」：auth 和 user 两个子路由都挂在它下面
# 这就是教学视频 main.py 里 app.include_router(api) 用的那个 api 对象
from app.api import api

# 导入异常处理器注册函数：把自定义异常统一包成标准响应格式
from app.utils.main import register_exception_handlers

# 定义「生命周期」函数：FastAPI 在对外提供服务之前，会先执行 yield 之前的代码
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 尝试连接数据库，并把模型里定义的表创建出来（已存在的表不会被动到）
    try:
        init_db()
        print("[启动] 数据库表已就绪")
    except Exception as exc:
        # 连不上数据库时只打印提示，不让整个服务直接启动失败
        print(f"[启动] 数据库初始化失败：{exc}")

    # 首次启动且数据表为空时，写入演示数据（实验室 + 设备）
    # 已在里面做了「表为空才插入」的判断，重复启动不会重复写入
    try:
        from app.seed import seed_data
        seed_data()
        print("[启动] 演示数据已就绪（若表已有数据则跳过）")
    except Exception as exc:
        # 演示数据写入失败不影响主服务启动
        print(f"[启动] 演示数据写入失败：{exc}")

    # 启动时顺手执行一次「过期预约自动结束」：演示 service 定时任务的调用方式
    # （service 定时任务按分层规范自己用 SessionLocal 开会话，不依赖请求）
    # 真正的周期调度（如每小时跑一次）以后接调度框架时，把同一个函数挂上去即可
    try:
        from app.services.appointment_service import exp_end_pending_reservations
        ended = exp_end_pending_reservations()
        print(f"[启动] 过期预约自动结束：{ended} 条")
    except Exception as exc:
        # 清理失败不影响主服务启动
        print(f"[启动] 过期预约处理失败：{exc}")

    # 启动时预加载 RAG 答疑知识库：把 knowledge/ 下的 Markdown 解析、向量化后
    # 装入 ChromaDB 内存向量库（毫秒级完成），供 AI 助手检索使用；
    # 加载失败不影响主服务：AI 助手会自动退化为「仅靠系统提示词回答」
    try:
        from app.services import kb_service
        kb_count = kb_service.build_index()
        print(f"[启动] RAG 知识库已加载：{kb_count} 条")
    except Exception as exc:
        print(f"[启动] RAG 知识库加载失败：{exc}")
    # yield 之后，服务正式开始接收请求；服务关闭时才会继续执行后面的代码
    yield

# 创建 FastAPI 应用对象；标题来自 .env，lifespan 绑定上面的启动逻辑
app = FastAPI(
    title=settings.API_TITLE,
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# 允许前端 Vite 开发服务器（5173 端口）跨域访问后端
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册业务路由：总路由 api 自带 /api 前缀，里面已经汇总了
# POST /api/auth/login 和 GET /api/user/info
# 以后新增实验室 / 设备模块，去 app/api/__init__.py 里 include 一次即可
app.include_router(api)

# ========== 文件上传支持 ==========
# 启动时确保上传根目录存在（exist_ok=True：已存在就跳过不报错）
# 目录必须先建好，下面 StaticFiles 挂载时会检查目录是否存在
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

# 把 /uploads 映射到磁盘上传目录：访问 /uploads/<分类>/<年>/<月>/<日>/<文件名> 就能直接显示图片
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# 注册全局异常处理器：业务里 raise 的异常会被自动捕获成统一格式返回
# （函数定义在 app/utils/main.py，对应视频里 main.py 的「注册自定义异常」那段）
register_exception_handlers(app)

# 期望加载的依赖清单：左边是「安装包名」，右边是「代码里 import 的模块名」
REQUIRED = {
    "fastapi": "fastapi",
    "uvicorn": "uvicorn",
    "starlette": "starlette",
    "pydantic": "pydantic",
    "python-multipart": "multipart",
    "httptools": "httptools",
    "watchfiles": "watchfiles",
    "websockets": "websockets",
    "SQLAlchemy": "sqlalchemy",
    "PyMySQL": "pymysql",
    "pydantic-settings": "pydantic_settings",
}


@app.get("/", summary="根路径")
def root():
    # 返回几个常用入口，方便在浏览器里点开查看
    return {
        "message": "智能预约系统后端已启动",
        "docs": "/docs",
        "health": "/health",
        "login": "POST /api/auth/login",
        "user_info": "GET /api/user/info",
    }


@app.get("/health", summary="环境、依赖与数据库健康检查")
def health():
    # 逐个导入依赖并记录版本，缺哪个包一眼就能看出来
    packages = {}
    for dist, module in REQUIRED.items():
        try:
            import_module(module)
            version = metadata.version(dist)
            packages[dist] = {"status": "ok", "version": version}
        except (ImportError, metadata.PackageNotFoundError) as exc:
            packages[dist] = {"status": "missing", "error": str(exc)}

    # 单独检查数据库：执行一句最简单的 SELECT 1，能成功就说明账号密码、库名都对了
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        # 注意：这里不返回连接串，避免把数据库密码暴露在接口响应里
        database = {"status": "ok", "check": "SELECT 1 成功"}
    except Exception as exc:
        database = {"status": "error", "error": str(exc)}

    # 只有所有依赖和数据库都正常，整体状态才是 ok
    all_ok = all(item["status"] == "ok" for item in packages.values()) and database["status"] == "ok"
    return {
        "status": "ok" if all_ok else "error",
        "python": python_version(),
        "database": database,
        "packages": packages,
    }


# 只有直接运行 python -m app.main 时才会走这里；用 uvicorn 命令启动时不会执行
if __name__ == "__main__":
    # 在函数内部导入，避免用命令行启动时多余加载
    import uvicorn

    # 注意：字符串必须写包名路径 app.main:app，不能写 main:app，否则热重载会找错模块
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
