# 用户信息接口：必须登录后才能访问
# 教学视频里这个文件在 backend/app/api/user.py，本项目源码根就是 backend，导入一律写 app.xxx

# APIRouter = 把一组接口打包成一个路由器；Depends = 依赖注入（自动完成登录校验）
# HTTPException / status 用于在数据非法时主动返回错误
# Query = 声明查询参数（分页、筛选条件）
from fastapi import APIRouter, Depends, HTTPException, Query, status

# Session = 给数据库会话参数做类型标注；or_ = SQL 里的「或」条件
from sqlalchemy.orm import Session
from sqlalchemy import or_

# 适配 1：视频写 app.models.user（复数），本项目目录是 model（单数）
from app.model.user import User

# 登录校验依赖：解析 token → 查库 → 检查账号状态 → 返回当前用户对象
from app.dependencies.auth import get_current_user

# 管理员权限依赖：role != admin 直接 403（账号管理是管理员专属功能）
from app.dependencies.permission import require_admin

# 适配 2：视频写 backend.app.schemas.user，本项目没有 backend 这个包
# UserResponse 用来控制返回给前端的字段，避免把密码等敏感信息带出去
# AccountResponse 是账号管理模块的响应模型（多了 create_time，同样不含密码）
from app.schemas.user import UserResponse, UpdateUserRequest, AccountResponse

# 导入数据库会话依赖（get_db）和统一返回工具（Response）
# 这两个都是从项目根公共目录导入：app.database / common.response
from app.database import get_db
from common.response import Response

# 子路由只写 /user；总路由 app/api/__init__.py 已经统一加了 /api
# 所以下面 /info 接口的完整路径是 GET /api/user/info
# tags=["用户信息"] 让它在 /docs 里归到「用户信息」分组
router = APIRouter(prefix="/user", tags=["用户信息"])


# 获取当前登录用户信息
@router.get("/info")
def get_user_info(current_user: User = Depends(get_current_user)):
    """获取当前登录用户信息"""
    # current_user 由 get_current_user 自动注入，已经是数据库里的 User 对象
    # 没带 token / token 失效 / 账号不存在或被禁用，依赖项会直接抛 401，走不到这里
    # 用统一返回工具，保持和项目其他接口一致的 {code, message, data} 结构
    return Response.success(
        message="请求成功",
        data=UserResponse.model_validate(current_user),
    )


# 更新当前登录用户的基本信息（名称 / 邮箱 / 手机号 / 头像）
@router.put("/info")
def update_user_info(
    # 请求体：只传要改的字段即可（其余保持原值）
    data: UpdateUserRequest,
    # 当前登录用户，由依赖项自动注入
    current_user: User = Depends(get_current_user),
    # 数据库会话，用于提交修改
    db: Session = Depends(get_db),
):
    """更新当前登录用户的基本信息"""
    # 1) 名称：对应库里的 real_name，不允许改成空
    if data.name is not None:
        if not data.name.strip():
            return Response.error(code=400, message="名称不能为空")
        current_user.real_name = data.name.strip()

    # 2) 邮箱：允许清空（传空字符串 → None）
    if data.email is not None:
        current_user.email = data.email.strip() or None

    # 3) 手机号：允许清空
    if data.phone is not None:
        current_user.phone = data.phone.strip() or None

    # 4) 头像：前端先调用上传接口得到 /uploads/... 链接后再传回来
    if data.avatar is not None:
        current_user.avatar = data.avatar

    # 把改动写入数据库
    db.commit()
    db.refresh(current_user)

    # 返回最新的用户信息，前端直接用它刷新页面
    return Response.success(
        message="更新成功",
        data=UserResponse.model_validate(current_user),
    )


# ==================== 账号管理模块（第 33 步，仅管理员） ====================

# 分页查询所有账号：支持关键字（账号/姓名模糊）、角色、状态筛选
# 完整路径：GET /api/user/list
@router.get("/list")
def list_users(
    # 页码从 1 开始，最小 1
    page: int = Query(1, ge=1),
    # 每页条数：1~100
    page_size: int = Query(10, ge=1, le=100),
    # 关键字：同时模糊匹配登录账号和姓名
    keyword: str | None = Query(None, description="关键字：匹配账号或姓名"),
    # 角色筛选：admin=管理员 / student=学生；不传查全部
    role: str | None = Query(None, description="角色筛选：admin/student"),
    # 状态筛选：1=启用，0=禁用；不传查全部
    status: int | None = Query(None, description="状态筛选：1启用 0禁用"),
    # 数据库会话
    db: Session = Depends(get_db),
    # 管理员权限校验：学生调这个接口直接 403
    _: User = Depends(require_admin),
):
    """管理员分页查询系统里所有账号"""
    # 构建基础查询
    query = db.query(User)
    # 关键字模糊匹配「账号」或「姓名」两列（or_ = SQL 的 OR）
    if keyword:
        kw = f"%{keyword}%"
        query = query.filter(
            or_(User.username.contains(kw), User.real_name.contains(kw))
        )
    # 角色筛选（status=0 这类值也有效，所以用 is not None 判断是否传了参数）
    if role is not None:
        query = query.filter(User.role == role)
    # 状态筛选
    if status is not None:
        query = query.filter(User.status == status)
    # 总数（给前端分页组件显示「共 X 条」）
    total = query.count()
    # 分页取数据：按 id 升序（账号列表习惯从早到晚），跳过前面页、取本页
    items = (
        query.order_by(User.id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    # 用 AccountResponse 序列化：它没有 password 字段，密码绝不会泄出去
    return Response.success(
        data={
            "list": [AccountResponse.model_validate(u) for u in items],
            "total": total,
        }
    )


# 查看单个账号详情
# 完整路径：GET /api/user/detail/{id}
# 注意：路径用 /detail/{id} 而不是 /{id}，避免和已有的 /api/user/info 产生路由歧义
@router.get("/detail/{user_id}")
def get_user_detail(
    # 路径参数：账号 ID
    user_id: int,
    # 数据库会话
    db: Session = Depends(get_db),
    # 管理员权限校验：学生调这个接口直接 403
    _: User = Depends(require_admin),
):
    """管理员查看单个账号的完整信息（只读，不含密码）"""
    user = db.query(User).filter(User.id == user_id).first()
    # 账号不存在 → 404
    if not user:
        raise HTTPException(status_code=404, detail="账号不存在")
    # AccountResponse 只声明了安全字段，password 不在其中
    return Response.success(data=AccountResponse.model_validate(user))
