# 权限依赖：区分「管理员专属」和「普通登录用户」接口
# 用法：在接口参数里写 current_user: User = Depends(require_admin)，
#      只有 role=admin 的用户才能进来；学生访问会直接拿到 403

# FastAPI 工具：HTTPException 抛 HTTP 错误，status 提供状态码常量
from fastapi import Depends, HTTPException, status

# 复用登录校验依赖：先确认已登录、拿到当前用户对象
from app.dependencies.auth import get_current_user

# 用户表模型
from app.model.user import User


def require_admin(current_user: User = Depends(get_current_user)):
    """管理员专属依赖：不是管理员就直接 403 拒绝"""
    # 角色不是 admin（比如 student），没有权限进入管理员接口
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="无权限访问"
        )
    # 是管理员，把用户对象往下传，业务接口可以直接用
    return current_user
