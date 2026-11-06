# 智能预约系统 · 后端「文件上传接口」实现方案

> **本文档用途**：整份交给 AI（Cursor / ChatGPT / 通义等），让它按此在现有 FastAPI 项目中实现文件上传功能。
>
> **项目路径**：后端根目录 `D:\智能预约系统\cursor\backend`
> **技术栈**：Python 3.13 + FastAPI + SQLAlchemy + MySQL + JWT
> **运行命令**：在 `backend` 目录下执行 `.\.venv\Scripts\uvicorn.exe app.main:app --reload`

---

## 0. 给 AI 的任务指令

请在现有 FastAPI 后端中新增「文件上传」能力，要求：

1. 严格遵守下面「现有项目约定」，不要改变已有接口的返回格式；
2. 按第 4 节的「文件清单」新增 / 修改文件，代码可直接采用第 5 节的完整实现；
3. 完成后按第 8 节「验收标准」逐条自测；
4. 所有新增代码沿用现有风格：**逐行中文注释**。

---

## 1. 现有项目约定（实现时必须遵守）

| 约定 | 说明 |
|---|---|
| 统一响应信封 | 所有接口返回 `{code, message, data}`，成功用 `Response.success(...)`（来自 `common/response.py`） |
| 业务异常 | 主动报错用 `BusinessException("提示", code=400)`（来自 `common/exceptions.py`），全局处理器会自动包装成统一信封 |
| 路由汇总 | 各模块的 `APIRouter` 汇总在 `app/api/__init__.py`，总前缀 `/api` |
| 登录校验 | 需要登录的接口写 `current_user: User = Depends(get_current_user)`（来自 `app/dependencies/auth.py`） |
| 导入路径 | 源码根就是 `backend`，导入一律写 `app.xxx` / `common.xxx`，**不要**写 `backend.app.xxx` |
| 目录职责 | `model/` 存表模型，`schemas/` 存接口输入输出模板，`api/` 存接口，`utils/` 存工具函数 |
| 依赖 | `python-multipart` 已在 requirements 中（上传表单需要），无需新增依赖 |

---

## 2. 接口契约

```
POST /api/upload
  Header : Authorization: Bearer <token>     # 必须登录
  Body   : multipart/form-data
           file      (必填) 文件
           category  (可选) avatar / lab / device / common，默认 common

成功 200:
{
  "code": 200,
  "message": "上传成功",
  "data": {
    "url": "/uploads/avatar/2026/11/05/3f2a9c...e1.png",
    "filename": "3f2a9c...e1.png",
    "size": 123456
  }
}

失败 400（不支持的扩展名 / 超过大小限制）:
{ "code": 400, "message": "不支持的文件类型：exe" }
```

> 返回的 `url` 是**相对路径**，前端拼完整地址（配合 vite 代理，或后端返回绝对地址）。

---

## 3. 存储设计

- 存本地磁盘：`backend/uploads/`（开发环境够用；生产再换 OSS / MinIO）
- 目录结构：`uploads/<category>/<年>/<月>/<日>/<uuid>.<ext>`
- 文件名用 **UUID 重命名**：防同名覆盖、防路径穿越
- 扩展名白名单 + 大小上限由 `.env` / `config` 配置

---

## 4. 文件清单

| 文件 | 动作 |
|---|---|
| `app/config.py` | 追加 3 个配置项 |
| `app/utils/file.py` | **新建**：保存文件 + 校验 |
| `app/api/upload.py` | **新建**：上传接口 |
| `app/api/__init__.py` | 注册 upload 路由 |
| `app/main.py` | 挂载 `/uploads` 静态目录 |
| `.gitignore` | 忽略 `uploads/` |
| `../frontend/vite.config.ts` | 增加 `/uploads` 代理（前端在 `cursor/frontend`） |

---

## 5. 完整代码

### 5.1 `app/config.py` —— 在 Settings 类里追加

```python
# 上传相关配置（追加在 Settings 类中，写法与现有字段保持一致）
UPLOAD_DIR: str = "uploads"                        # 上传文件存放目录（相对 backend 根目录）
MAX_UPLOAD_SIZE_MB: int = 5                        # 单个文件大小上限（MB）
ALLOWED_EXTENSIONS: str = "jpg,jpeg,png,gif,webp"  # 允许的扩展名，逗号分隔
```

### 5.2 `app/utils/file.py` —— 新建

```python
# 文件上传工具：校验 + 保存
import os
import uuid
from datetime import datetime

from app.config import settings
from common.exceptions import BusinessException

# 把 "jpg,jpeg,png" 字符串解析成集合，方便判断
ALLOWED = {ext.strip().lower() for ext in settings.ALLOWED_EXTENSIONS.split(",")}

# 大小上限换算成字节
MAX_BYTES = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024


def save_upload(file, category: str = "common") -> dict:
    """保存上传文件，返回 {url, filename, size}"""
    # 1. 校验扩展名（只取原文件名的扩展名，不信任文件名本身）
    ext = os.path.splitext(file.filename or "")[1].lower().lstrip(".")
    if ext not in ALLOWED:
        raise BusinessException(f"不支持的文件类型：{ext or '未知'}", code=400)

    # 2. 按 分类/年/月/日 生成目录
    now = datetime.now()
    rel_dir = os.path.join(
        category, now.strftime("%Y"), now.strftime("%m"), now.strftime("%d")
    )
    abs_dir = os.path.join(settings.UPLOAD_DIR, rel_dir)
    os.makedirs(abs_dir, exist_ok=True)

    # 3. 用 UUID 重命名，防止同名覆盖和路径穿越
    filename = f"{uuid.uuid4().hex}.{ext}"
    abs_path = os.path.join(abs_dir, filename)

    # 4. 分块写入，边写边算大小，超过上限立刻删除
    size = 0
    out = open(abs_path, "wb")
    try:
        while True:
            chunk = file.file.read(1024 * 1024)  # 每次读 1MB
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_BYTES:
                out.close()
                os.remove(abs_path)
                raise BusinessException(
                    f"文件不能超过 {settings.MAX_UPLOAD_SIZE_MB}MB", code=400
                )
            out.write(chunk)
    finally:
        if not out.closed:
            out.close()

    # 5. 拼出可直接访问的相对地址（注意 Windows 用 os.sep，转成 /）
    url = f"/uploads/{rel_dir.replace(os.sep, '/')}/{filename}"
    return {"url": url, "filename": filename, "size": size}
```

### 5.3 `app/api/upload.py` —— 新建

```python
# 文件上传接口：必须登录后才能传
from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.dependencies.auth import get_current_user
from app.model.user import User
from app.utils.file import save_upload
from common.response import Response

# 子路由只写 /upload；总路由 app/api/__init__.py 会补上 /api
# 最终完整路径：POST /api/upload
router = APIRouter(prefix="/upload", tags=["文件上传"])


@router.post("", summary="上传文件")
def upload(
    file: UploadFile = File(...),           # 必填：表单里的文件
    category: str = Form("common"),         # 可选：avatar / lab / device
    current_user: User = Depends(get_current_user),  # 必须登录
):
    info = save_upload(file, category)
    return Response.success(message="上传成功", data=info)
```

### 5.4 `app/api/__init__.py` —— 注册路由（追加到文件末尾）

```python
# 注册文件上传路由 → 最终 POST /api/upload
from app.api.upload import router as upload_router

api.include_router(upload_router)
```

### 5.5 `app/main.py` —— 挂载静态目录（追加）

```python
# 顶部追加导入
import os
from fastapi.staticfiles import StaticFiles

# 在 app = FastAPI(...) 之后、include_router 附近追加：
# 确保上传目录存在，再把 /uploads 映射到本地目录，浏览器可直接访问图片
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")
```

### 5.6 `backend/.gitignore` —— 追加

```text
uploads/
```

### 5.7 `cursor/frontend/vite.config.ts` —— 给 `/uploads` 也加代理

```ts
export default defineConfig({
  plugins: [ /* 保持不变 */ ],
  resolve: { /* 保持不变 */ },
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8000',
      '/uploads': 'http://127.0.0.1:8000',   // ★ 新增：让 <img src="/uploads/..."> 能显示
    },
  },
})
```

---

## 6. 可选：想记录「谁传了什么」就加一张表

```python
# app/model/file.py（新建）
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class FileRecord(Base):
    """上传文件记录表"""
    __tablename__ = "file"
    __table_args__ = {"comment": "上传文件记录"}

    filename: Mapped[str] = mapped_column(String(255), comment="存储文件名")
    url: Mapped[str] = mapped_column(String(500), comment="访问地址")
    size: Mapped[int] = mapped_column(Integer, comment="字节数")
    mime: Mapped[str | None] = mapped_column(String(100), comment="MIME 类型")
    uploader_id: Mapped[int | None] = mapped_column(Integer, comment="上传用户 id")
```

> 若采用：在 `app/main.py` 的 `init_db()` 里导入该模型（`from app.model.file import FileRecord`），并在 `upload` 接口里 `db.add(...)` + `db.commit()`。

---

## 7. 前端调用示例（Element Plus）

```vue
<el-upload
  action="/api/upload"
  name="file"
  :headers="{ Authorization: 'Bearer ' + localStorage.getItem('token') }"
  :data="{ category: 'avatar' }"
  :show-file-list="false"
  @success="onUploadSuccess"
  @error="onUploadError"
/>
```

```ts
// 上传成功回调：后端返回的是 {code, message, data}
const onUploadSuccess = (resp: any) => {
  // el-upload 的 success 回调里 resp 是 HTTP 响应体（未经过 request 拦截器）
  if (resp.code !== 200) {
    ElMessage.error(resp.message)
    return
  }
  const url = resp.data.url   // "/uploads/avatar/2026/11/05/xxx.png"
  // 直接可给 <img :src="url"> 用（靠 vite 的 /uploads 代理）
  ElMessage.success('上传成功')
}
```

> 更严谨：用 `el-upload` 的 `http-request` 自定义，改走项目里的 `request` 实例（自动带 token、统一处理错误）。

---

## 8. 验收标准

| # | 操作 | 期望 |
|---|---|---|
| 1 | 不带 token 直接 POST `/api/upload` | 401 `登录已失效` |
| 2 | 带 token 上传一张 `.png` | `code:200`，`data.url` 形如 `/uploads/avatar/2026/11/05/xxx.png` |
| 3 | 看磁盘 | `backend/uploads/avatar/年/月/日/xxx.png` 存在 |
| 4 | 上传 `.exe` | `code:400`「不支持的文件类型：exe」 |
| 5 | 上传超过 5MB 的图 | `code:400`「文件不能超过 5MB」 |
| 6 | 浏览器打开 `http://localhost:5173/uploads/...`（走 vite 代理） | 能看到图片 |
| 7 | 刷新页面 / 重复上传同名文件 | 不覆盖（UUID 保证唯一） |

---

## 9. 注意事项 / 避坑

1. **大小必须分块校验**：边读边累加，超限立即删文件，否则大文件会撑爆内存；
2. **不要用原始文件名拼路径**：只用扩展名，路径自己生成，避免 `../../` 路径穿越；
3. **上传接口必须登录**：`Depends(get_current_user)`，否则任何人都能往服务器塞文件；
4. **`uploads/` 必须进 `.gitignore`**：别把用户文件提交进仓库；
5. **静态目录不要和代码混放**：固定放 `backend/uploads/`；
6. **uvicorn 的工作目录是 `backend`**，所以 `UPLOAD_DIR = "uploads"` 会解析到 `backend/uploads`，不要改成别的相对路径；
7. **本地磁盘只适合开发**，正式上线换对象存储（OSS / MinIO）并加防盗链、CDN；
8. 前端展示图片需要 `/uploads` 代理（见 5.7），否则 `<img src="/uploads/...">` 会 404。
