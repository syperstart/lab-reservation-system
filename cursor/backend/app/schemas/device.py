# 设备相关的请求 / 响应数据模型
from pydantic import BaseModel, ConfigDict, Field

# 设备响应模型：返回给前端时附带所属实验室名称（lab_name）
class DeviceResponse(BaseModel):
    id: int
    # 所属实验室 ID
    lab_id: int
    # 所属实验室名称（接口层关联查询后填入，方便前端直接显示）
    lab_name: str | None = None
    # 设备名称
    name: str
    # 图片 URL（可空）
    image: str | None = None
    # 型号规格（可空）
    model: str | None = None
    # 数量（至少 1）
    quantity: int
    # 状态：1=正常，0=维修
    status: int
    # 说明（可空）
    description: str | None = None

    model_config = ConfigDict(from_attributes=True)


# 新增设备请求模型
class DeviceCreate(BaseModel):
    # 所属实验室 ID：必填
    lab_id: int = Field(description="所属实验室ID")
    # 设备名称：必填
    name: str = Field(min_length=1, description="设备名称")
    # 图片 URL：选填（上传后由前端回填）
    image: str | None = None
    # 型号规格：选填
    model: str | None = None
    # 数量：选填，默认 1，至少 1
    quantity: int = Field(default=1, ge=1, description="数量，至少1")
    # 状态：选填，默认 1 正常，只能 0(维修) 或 1(正常)
    status: int = Field(default=1, ge=0, le=1, description="状态: 1-正常 0-维修")
    # 说明：选填
    description: str | None = None


# 修改设备请求模型：字段都可选，只更新传了的字段
class DeviceUpdate(BaseModel):
    lab_id: int | None = None
    name: str | None = Field(default=None, min_length=1)
    image: str | None = None
    model: str | None = None
    # 数量若传，至少 1
    quantity: int | None = Field(default=None, ge=1)
    # 状态若传，只能 0 或 1
    status: int | None = Field(default=None, ge=0, le=1)
    description: str | None = None
