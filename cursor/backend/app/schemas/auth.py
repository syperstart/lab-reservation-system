# 从 Pydantic 导入 BaseModel：它是所有「数据校验模型」的父类
# 用来定义请求 / 响应的数据结构，并自动做类型校验
from pydantic import BaseModel
from app.schemas.user import UserResponse
from app.model.user import User


# 登录请求模型：前端提交「用户名 + 密码」时，后端就用这个结构来接收
# 用法示例：在接口里写 data: LoginRequest，FastAPI 会自动把请求体转成这个对象
class LoginRequest(BaseModel):
    username: str
    password: str


# 注册请求模型：前端注册时提交这三个字段
class RegisterRequest(BaseModel):
    username: str
    password: str
    real_name: str | None = None   # 姓名，不填就用用户名

