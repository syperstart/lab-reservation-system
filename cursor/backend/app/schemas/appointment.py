# 预约相关的请求 / 响应数据模型
from pydantic import BaseModel, ConfigDict, Field

# 导入日期 / 时间类型，用于预约日期和起止时间的校验与序列化
from datetime import date, time


# 预约响应模型：返回给前端时附带实验室 / 设备 / 用户名称，避免前端二次请求
class AppointmentResponse(BaseModel):
    id: int
    # 预约学生 ID
    user_id: int
    # 所属实验室 ID
    lab_id: int
    # 设备 ID（可空）
    device_id: int | None = None
    # 预约日期
    appoint_date: date
    # 开始时间
    start_time: time
    # 结束时间
    end_time: time
    # 用途（可空）
    purpose: str | None = None
    # 状态：0=待审核，1=已通过，2=已拒绝，3=已取消
    status: int
    # 实验室名称（接口关联查询填入）
    lab_name: str | None = None
    # 设备名称（可空）
    device_name: str | None = None
    # 预约学生姓名（接口关联查询填入）
    user_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


# 提交预约请求模型（学生端）
class AppointmentCreate(BaseModel):
    # 实验室 ID：必填
    lab_id: int = Field(description="实验室ID")
    # 设备 ID：选填（不指定设备只约实验室）
    device_id: int | None = None
    # 预约日期：必填（格式 YYYY-MM-DD）
    appoint_date: date = Field(description="预约日期")
    # 开始时间：必填（格式 HH:MM:SS 或 HH:MM）
    start_time: time = Field(description="开始时间")
    # 结束时间：必填
    end_time: time = Field(description="结束时间")
    # 用途：选填
    purpose: str | None = None


# 预约审核请求模型（管理员端）
class AppointmentReview(BaseModel):
    # 审核结果：1=通过，2=拒绝（只能对待审核的预约审核）
    status: int = Field(description="1通过 / 2拒绝")
    # 拒绝原因（选填，后端暂不持久化，仅作参数接收）
    reason: str | None = None
