# 文件上传工具：负责「校验扩展名 → 按日期分目录保存 → 统计大小 → 返回访问 URL」
# 保存路径形如：uploads/<分类>/<年>/<月>/<日>/<uuid>.<扩展名>
# 用 uuid 重命名：原文件名完全不参与路径，从根本上防止「同名覆盖」和「路径穿越」

# os：拼路径 / 建目录 / 删文件
import os

# re：用正则校验分类名（category）是否合法
import re

# uuid4().hex：生成 32 位随机文件名（不带横线）
from uuid import uuid4

# datetime：取当前年月日，用来拼日期目录
from datetime import datetime

# UploadFile：FastAPI 的上传文件对象（支持异步分块读取）
from fastapi import UploadFile

# 读配置：上传根目录、大小上限、扩展名白名单
from app.config import settings

# 业务异常：校验不通过时抛出，全局异常处理器会包成统一格式返回
from common.exceptions import BusinessException

# 每次读取的块大小：1MB（大文件也不会一次性占满内存）
CHUNK_SIZE = 1024 * 1024

# 分类名只允许字母 / 数字 / 下划线 / 中划线（1~32 位）
# 防止 category=../../ 这种写法把文件写到 uploads 外面（路径穿越）
_CATEGORY_RE = re.compile(r"^[A-Za-z0-9_-]{1,32}$")


async def save_upload(file: UploadFile, category: str = "common") -> dict:
    """保存上传文件：校验 → 落盘 → 返回 {url, filename, size}

    file:     FastAPI 接收到的上传文件
    category: 存储分类（如 avatar），决定第一层子目录名
    返回:      url=可访问的相对地址, filename=磁盘上实际的文件名, size=字节数
    """
    # ---- 1. 校验分类名：不合法直接拒绝（防止用 category 拼出越界路径） ----
    if not _CATEGORY_RE.match(category or ""):
        raise BusinessException("分类名不合法", code=400)

    # ---- 2. 只取原文件名的扩展名做白名单校验 ----
    # splitext("a/b/evil.png")[1] 取出 ".png"，原名里的目录部分用不到、也不安全
    ext = os.path.splitext(file.filename or "")[1].lstrip(".").lower()
    # 把配置里的 "jpg,jpeg,png,gif,webp" 拆成集合，方便快速判断
    allowed = {e.strip().lower() for e in settings.ALLOWED_EXTENSIONS.split(",") if e.strip()}
    # 扩展名为空（没后缀）或不在白名单 → 报「不支持的文件类型」
    if not ext or ext not in allowed:
        raise BusinessException("不支持的文件类型", code=400)

    # ---- 3. 生成保存路径：<分类>/<年>/<月>/<日>/<uuid>.<ext> ----
    now = datetime.now()
    # 相对目录：avatar/2026/11/05（月、日补零成两位）
    rel_dir = os.path.join(category, str(now.year), f"{now.month:02d}", f"{now.day:02d}")
    # 绝对目录：uploads/avatar/2026/11/05
    abs_dir = os.path.join(settings.UPLOAD_DIR, rel_dir)
    # 按需创建多级目录（exist_ok=True：已存在不报错）
    os.makedirs(abs_dir, exist_ok=True)
    # uuid4().hex 重命名：同名文件也不会互相覆盖，也藏得住原文件名
    filename = f"{uuid4().hex}.{ext}"
    # 最终落盘的完整路径
    abs_path = os.path.join(abs_dir, filename)

    # ---- 4. 分块读取（每块 1MB）边写边统计大小，超限立即删文件并报错 ----
    # 大小上限换算成字节：5MB → 5 * 1024 * 1024
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    # 已写入的字节数
    size = 0
    # 是否超过上限的标记（超限要等文件关闭后才能删：Windows 删不掉已打开的文件）
    too_large = False
    try:
        # 二进制方式打开目标文件，边读边写
        with open(abs_path, "wb") as out:
            while True:
                # 异步读一块（最多 1MB）；返回空 bytes 表示读完了
                chunk = await file.read(CHUNK_SIZE)
                if not chunk:
                    break
                # 累加已接收的字节数
                size += len(chunk)
                # 超过上限：停止写入，退出循环后统一删文件
                if size > max_bytes:
                    too_large = True
                    break
                # 没超限才真正写盘
                out.write(chunk)
    except Exception:
        # 写盘中途出错（比如磁盘满）：清掉半截文件，不留垃圾
        if os.path.exists(abs_path):
            os.remove(abs_path)
        # 把原异常继续抛出去
        raise
    finally:
        # 无论成功失败，都要关闭上传文件的句柄，释放临时资源
        await file.close()

    # 超限处理：此时 with 已把文件关闭，Windows 下也能正常删除
    if too_large:
        os.remove(abs_path)
        raise BusinessException(f"文件不能超过 {settings.MAX_UPLOAD_SIZE_MB}MB", code=400)

    # ---- 5. 拼返回值 ----
    # 相对 URL：uploads/avatar/2026/11/05/xxx.png
    # Windows 下 os.sep 是反斜杠，统一替换成 /，前端才能直接当 <img src> 用
    url = "/" + os.path.join("uploads", rel_dir, filename).replace(os.sep, "/")
    # filename 是磁盘上实际保存的名字（uuid 重命名后），size 是字节数
    return {"url": url, "filename": filename, "size": size}
