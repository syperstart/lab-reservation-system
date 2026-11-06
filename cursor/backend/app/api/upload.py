# 文件上传接口：登录用户上传图片 → 校验 → 存到本地 uploads 目录 → 返回可访问的 URL
# 最终对外地址：POST /api/upload
# （/api 来自 app/api/__init__.py 总路由前缀，/upload 来自本文件 router 的前缀）

# APIRouter：子路由容器；File/Form：接表单里的文件和普通字段；UploadFile：上传文件类型
from fastapi import APIRouter, Depends, File, Form, UploadFile

# 登录校验依赖：带了有效 token 才放行，没带 / 过期直接 401
from app.dependencies.auth import get_current_user

# 用户模型：给 current_user 做类型标注
from app.model.user import User

# 文件保存工具：校验扩展名 + 分块落盘 + 返回 url/filename/size
from app.utils.file import save_upload

# 统一响应信封 Response.success / Response.error
from common.response import Response

# 创建上传子路由：前缀 /upload，/docs 文档里归到「文件上传」分组
# 注意：前缀不带 /api，/api 由 app/api/__init__.py 的总路由统一加（项目现有规范）
router = APIRouter(prefix="/upload", tags=["文件上传"])


# POST /api/upload：表单上传（multipart/form-data）
# 路径写 ""：和前缀拼起来正好是 /upload，最终地址就是 /api/upload
@router.post("", summary="上传图片")
async def upload(
    # 表单里的文件字段，必填；没传会走 422 参数校验
    file: UploadFile = File(...),
    # 表单里的普通字段：存储分类（如 avatar），不传默认 common
    category: str = Form("common"),
    # 依赖注入当前登录用户：这一步就是「必须登录」的开关，没带 token 到不了函数体
    current_user: User = Depends(get_current_user),
):
    # 调用工具函数完成校验 + 落盘，拿到 {url, filename, size}
    info = await save_upload(file, category)
    # 用统一信封返回：data 里就是上面的 info
    return Response.success(message="上传成功", data=info)
