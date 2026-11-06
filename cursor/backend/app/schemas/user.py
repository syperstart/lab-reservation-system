# 从 Pydantic 导入 BaseModel、ConfigDict 和 Field
# BaseModel = 数据模型父类；ConfigDict = 配置模型行为（比如能否从 ORM 对象读属性）
# Field = 给字段加校验 / 别名，这里用来把数据库字段 real_name 映射到响应字段 name
from pydantic import BaseModel, ConfigDict, Field


# 用户响应模型：接口把用户信息返回给前端时，统一用这个结构
# 这样可以只暴露需要的字段，避免把密码等敏感信息也返回出去
class UserResponse(BaseModel):
    # 用户主键 ID
    id: int

    # 姓名：数据库 User 里对应的字段叫 real_name，不是 name
    # 适配：用 validation_alias 做别名映射，这样视频里的
    # UserResponse.model_validate(current_user) 才能直接从 ORM 对象取值，
    # 否则会因为找不到 name 属性而抛 ValidationError
    name: str = Field(validation_alias="real_name")

    # 邮箱：可能为空，所以类型写成 str | None，并给默认值 None
    email: str | None = None

    # 手机号：同样可能为空
    phone: str | None = None

    # 状态：1 = 正常，0 = 禁用
    status: int

    # 登录账号：User 表里的 username 字段，个人信息页用来展示「账号」并设为只读
    username: str

    # 角色：admin=管理员 / student=学生，个人信息页用来展示「角色」并设为只读
    role: str

    # 头像地址：可能为空，前端展示时用默认头像兜底
    avatar: str | None = None

    # from_attributes=True 表示：可以直接用 ORM 对象来构造这个响应模型
    # 例如：UserResponse.model_validate(orm_user)
    # 注意：模型里的字段名要和 ORM 对象的属性名一致，否则取不到值；
    # 本项目 app/model/user.py 里的字段是 username / real_name / role / email / phone / avatar / status，
    # name 已经用上面的 validation_alias="real_name" 解决，其余字段同名可直接取
    # populate_by_name=True 保证原来 UserResponse(name=..., ...) 这种手动构造方式仍然可用
    # （api/auth.py 登录接口就是这样写的，不能破坏）
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# 更新用户信息请求模型：个人信息页「保存修改」时提交的数据
# 所有字段都允许不传（可选），这样前端可以只改其中一部分（比如只改邮箱）
class UpdateUserRequest(BaseModel):
    # 名称：对应数据库里的 real_name；空字符串会被接口拒绝
    name: str | None = None

    # 邮箱：可为空（传空字符串表示清空）
    email: str | None = None

    # 手机号：可为空
    phone: str | None = None

    # 头像地址：由前端先调用上传接口得到 /uploads/... 链接再传回来
    avatar: str | None = None


# ===== 账号管理模块（第 33 步）：管理员查看系统所有账号用的响应模型 =====
# 注意 datetime 类型需要先导入
from datetime import datetime

# 账号管理响应模型：字段比 UserResponse 多一个 create_time（创建时间）
# 关键安全点：**不定义 password 字段**，model_validate 只会挑这里声明过的字段，
# 因此即使数据库里有密码（哪怕是明文），也绝不会随接口返回出去
class AccountResponse(BaseModel):
    # 用户主键 ID
    id: int

    # 登录账号
    username: str

    # 姓名：库里叫 real_name，用别名映射（和 UserResponse 同一套做法）
    name: str = Field(validation_alias="real_name")

    # 角色：admin=管理员 / student=学生
    role: str

    # 邮箱：可能为空
    email: str | None = None

    # 手机号：可能为空
    phone: str | None = None

    # 头像地址：可能为空，前端用首字色块兜底
    avatar: str | None = None

    # 状态：1=启用，0=禁用
    status: int

    # 创建时间：登录时写入、之后不变；datetime 会序列化成 ISO 字符串
    create_time: datetime

    # 允许直接从 ORM 对象取值；populate_by_name 保证别名映射下手动构造也可用
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
