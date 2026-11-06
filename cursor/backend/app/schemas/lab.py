# 实验室相关的请求 / 响应数据模型（用 Pydantic 做字段校验和序列化）
from pydantic import BaseModel, ConfigDict, Field

# 实验室响应模型：接口把实验室信息返回给前端时使用
# from_attributes=True 表示可以直接从 ORM 对象（Lab）构造
class LabResponse(BaseModel):
    # 主键 ID
    id: int
    # 名称
    name: str
    # 编号
    code: str
    # 位置（可空）
    location: str | None = None
    # 可容纳人数（可空）
    capacity: int | None = None
    # 描述（可空）
    description: str | None = None
    # 状态：1=启用，0=停用
    status: int

    model_config = ConfigDict(from_attributes=True)


# 新增实验室请求模型：前端提交的数据格式
class LabCreate(BaseModel):
    # 名称：必填，去掉首尾空格
    name: str = Field(min_length=1, description="实验室名称")
    # 编号：必填
    code: str = Field(min_length=1, description="实验室编号")
    # 位置：选填
    location: str | None = None
    # 容量：选填
    capacity: int | None = None
    # 描述：选填
    description: str | None = None
    # 状态：选填，默认 1 启用
    status: int = 1


# 修改实验室请求模型：所有字段都允许不传（只改传上来的部分）
class LabUpdate(BaseModel):
    name: str | None = None
    code: str | None = None
    location: str | None = None
    capacity: int | None = None
    description: str | None = None
    status: int | None = None
