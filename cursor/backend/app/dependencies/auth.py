# 登录校验依赖：给「必须登录后才能访问」的接口用
# 用法：在接口参数里写 current_user: User = Depends(get_current_user)，
# FastAPI 就会先执行本函数，把当前登录用户对象交进去
# 说明：教学视频里这个文件位于 backend/app/dependencies/auth.py，
# 本项目的源码根就是 backend，所以导入一律写 app.xxx（写 backend.app.xxx 会找不到模块）

# 从 FastAPI 导入三个工具：
# Depends = 依赖注入，自动把令牌、数据库会话塞进函数参数
# HTTPException = 主动抛出 HTTP 错误（这里统一用 401 未授权）
# status = 状态码常量，写 status.HTTP_401_UNAUTHORIZED 比直接写数字 401 更清楚
from fastapi import Depends, HTTPException, status

# OAuth2PasswordBearer = 告诉 FastAPI 去请求头 Authorization: Bearer <token> 里取令牌
from fastapi.security import OAuth2PasswordBearer

# Session = 给数据库会话参数做类型标注
from sqlalchemy.orm import Session

# 适配 1：视频写 from backend.app.database import get_db，
# 本项目没有 backend 这个包，改成 app.database
from app.database import get_db

# 适配 2：视频写 from backend.app.utils.jwt import decode_access_token，同样改掉；
# decode_access_token 是这次顺手补进 app/utils/jwt.py 的函数（原来只有生成 token 的）
from app.utils.jwt import decode_access_token

# 适配 3：图二第 29 行用了 User，但两张截图里都没有导入它，
# 不补这一行会报「未解析的引用 User」
from app.model.user import User

# 创建「取令牌的规则」对象
# tokenUrl 只是告诉 /docs 文档「去哪个地址登录」，不会真的在这里发起登录请求
# 适配 4：视频写的是 "/api/authr/login"（多了一个 r，是笔误），
# 本项目登录接口实际是 /api/auth/login，按实际路径写
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


# 当前登录用户依赖：解析令牌 → 查数据库 → 检查账号状态 → 返回用户对象
def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
):
    # 第一步：解析令牌，取出里面存的 user_id
    # 令牌过期、签名不对、格式损坏都会抛异常，这里统一转成 401 让前端重新登录
    try:
        payload = decode_access_token(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="登录已失效，请重新登录"
        )

    # 获取到用户ID
    # payload 是字典，用 get 取不到时返回 None，不会抛 KeyError
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的登录凭证"
        )

    # 从数据库根据用户ID查询用户信息
    user = db.query(User).filter(User.id == user_id).first()

    # 补充 1：视频里没有这段。如果令牌里的 id 在数据库里查不到（比如用户被删了），
    # user 会是 None，直接取 user.status 会变成 500 错误，这里提前挡掉
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在"
        )

    # status 不是 1 说明账号被禁用（User.status：1=正常，0=禁用）
    if user.status != 1:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="用户被禁用"
        )

    # 补充 2：截图到第 33 行为止还没写 return，但依赖函数必须把用户交出去，
    # 否则业务接口里拿到的 current_user 永远是 None
    return user
