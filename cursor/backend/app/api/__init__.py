# 让 api 文件夹成为一个「Python 包（package）」
# 以后可以写 from app.api.auth import router
# 后续新增设备、实验室等接口，也都在这个文件夹里按模块拆分

# 下面是按教学视频补的「总路由」配置：把各业务子路由汇总成一个 api，
# main.py 里只要写一次 app.include_router(api) 就够了

# APIRouter = 路由容器，可以把多个子路由合并进来
from fastapi import APIRouter

# 导入登录模块的路由器，起别名避免和下面 user 的 router 重名
# 适配 1：视频截图第 2 行被浮动工具栏挡住了，但第 7 行用的是 auth_router，
# 所以这里必须写 as auth_router，否则会报 NameError
from app.api.auth import router as auth_router

# 导入用户信息模块的路由器，同样起别名
from app.api.user import router as user_router

# 导入文件上传模块的路由器，同样起别名
from app.api.upload import router as upload_router

# 导入实验室 / 设备 / 预约 三个业务模块的路由器
from app.api.lab import router as lab_router
from app.api.device import router as device_router
from app.api.appointment import router as appointment_router
from app.api.appointment import lab_public_router as lab_public_router

# 导入 AI 助手模块的路由器
from app.api.ai import router as ai_router

# 创建总路由，统一加 /api 前缀
# 子路由只写自己那一段：auth 写 /auth、user 写 /user、lab 写 /lab …
api = APIRouter(prefix="/api")

# 把登录路由挂进来 → 最终 POST /api/auth/login（对外地址和原来完全一样）
api.include_router(auth_router)

# 把用户信息路由挂进来 → 最终 GET /api/user/info
api.include_router(user_router)

# 把文件上传路由挂进来 → 最终 POST /api/upload
api.include_router(upload_router)

# 把「学生浏览实验室」路由挂进来 → /api/lab/available、/api/lab/{id}/devices
# 注意：必须放在 lab_router 之前，否则 /available 会被 admin 的 /{lab_id} 抢先匹配导致 403
api.include_router(lab_public_router)

# 把实验室管理路由挂进来 → 最终 /api/lab/...
api.include_router(lab_router)

# 把设备管理路由挂进来 → 最终 /api/device/...
api.include_router(device_router)

# 把预约路由挂进来 → 最终 /api/appointment/...
api.include_router(appointment_router)

# 把 AI 助手路由挂进来 → 最终 /api/ai/chat
api.include_router(ai_router)
