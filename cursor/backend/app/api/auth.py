# 从 FastAPI 导入 APIRouter 和 Depends：
# APIRouter = 把一组接口打包成一个小路由器，方便注册到主应用
# Depends = 依赖注入，用来在接口里自动拿到数据库会话
from fastapi import APIRouter, Depends

# 导入登录请求模型：前端提交「用户名 + 密码」时，用 LoginRequest 来接收并校验
from app.schemas.auth import LoginRequest, RegisterRequest

# 导入用户响应模型：登录成功后返回给前端的用户信息，用 UserResponse 控制要暴露哪些字段
from app.schemas.user import UserResponse

# 从 SQLAlchemy 导入 Session，用来给参数标注类型（db: Session）
from sqlalchemy.orm import Session

# 导入 get_db：接口里写 Depends(get_db)，FastAPI 就会自动塞一个数据库会话进来
from app.database import get_db

# 导入用户表模型 User，用它去数据库里查用户
from app.model.user import User

# 导入密码校验工具：verify_password(前端明文, 数据库里存的密码)
# 修正：原来写成 from cursor.backend.app.utils.password import ...，
# Python 里没有 cursor 这个包；项目根就是 backend，直接用 app.utils.password
from app.utils.password import verify_password, hash_password

# 导入 JWT 生成工具：登录成功后用它签发访问令牌 access_token
from app.utils.jwt import create_access_token
from common.response import Response
from common.exceptions import BusinessException

# 创建一个路由器：这里只写 /auth，总路由 app/api/__init__.py 会再补上 /api
# 适配：原来直接写 /api/auth，改成经总路由注册后会变成 /api/api/auth；
# 现在 /api + /auth + /login，最终地址仍是 POST /api/auth/login，前端不用改
# tags=["权限验证"] 表示在 /docs 文档里把这些接口归到「权限验证」分组下
router = APIRouter(prefix="/auth", tags=["权限验证"])


# 登录接口：完整路径是 POST /api/auth/login
# data: LoginRequest 会自动把请求体 JSON 转成 LoginRequest 对象
# db: Session = Depends(get_db) 会自动注入一个数据库会话
@router.post("/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    # 用前端传来的 username 去数据库 user 表里查第一条匹配的记录
    user = db.query(User).filter(User.username == data.username).first()

    # 判断账号是否存在 / 密码是否正确，不对就返回 400 错误
    # verify_password 返回 True 表示密码正确；not 取反表示「不正确」
    if not user or not verify_password(data.password, user.password):
        return {"code": 400, "message": "账号或密码错误"}

    # 验证账号状态：status != 1 表示账号被禁用，返回 403
    if user.status != 1:
        return {"code": 403, "message": "账号已被禁用"}

    # 账号密码都对，签发 JWT 令牌（令牌里装着 user_id，有效期来自 .env，当前 60 分钟）
    token = create_access_token(user.id)

    # 用统一的 Response.success 返回成功结果：
    # data 里放 token 和用户信息，用户敏感字段（如密码）不会带出去
    # UserResponse.model_validate(user) 会自动从 ORM 对象读取字段（含 real_name→name）
    return Response.success(
        message="登录成功",
        data={
            "token": token,
            "user": UserResponse.model_validate(user).model_dump(),
        },
    )


# 注册接口：完整路径 POST /api/auth/register（路由前缀 /auth 已经有了，不用改 api/__init__.py）
@router.post("/register")
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    # 1. 先查用户名是否被占用
    exists = db.query(User).filter(User.username == data.username).first()
    if exists:
        raise BusinessException("用户名已存在", code=400)

    # 2. 创建用户：密码一定要哈希后存，不能存明文
    user = User(
        username=data.username,
        real_name=data.real_name or data.username,  # 没填姓名就用用户名
        password=hash_password(data.password),      # 用现成的哈希工具
        role="student",                             # 自己注册的一律是学生
    )
    db.add(user)       # 加入待提交
    db.commit()        # 真正写进 database
    db.refresh(user)   # 回读一次，拿到自增的 id

    # 3. 返回用户信息（用 UserResponse，自动把密码挡掉）
    return Response.success(message="注册成功", data=UserResponse.model_validate(user))
