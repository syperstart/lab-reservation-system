# 预约管理接口（分层改造示范模块）：本文件现在只做三件事——
#   1. 接收 / 校验请求参数（路由、依赖注入、schema 反序列化）
#   2. 调用业务层 app/services/appointment_service.py
#   3. 把 service 返回的 dict/list 转成 schema，用 Response.success 统一返回
# 业务规则（时间校验、冲突检测、状态机）与数据库写入已全部下沉到 service；
# 接口路径、请求体字段、返回格式与迁移前完全一致，前端无需任何改动。
#
# 学生端「浏览实验室与设备」两个只读查询暂时留在本文件：
# 它们属于 lab 域的简单查询，等以后迁移 lab 模块时再挪进 lab_service。

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

# 登录校验 + 管理员权限依赖
from app.dependencies.auth import get_current_user
from app.dependencies.permission import require_admin

# 模型：学生浏览端点还要用到（业务端点已不需要模型，全部走 service）
from app.model.user import User
from app.model.lab import Lab
from app.model.device import Device

# 预约请求 / 响应模型
from app.schemas.appointment import (
    AppointmentResponse,
    AppointmentCreate,
    AppointmentReview,
)

# 设备响应模型（学生浏览设备列表用）
from app.schemas.device import DeviceResponse

# 预约业务层：所有业务逻辑都在这里
from app.services import appointment_service

# 数据库会话 + 统一响应
from app.database import get_db
from common.response import Response

# 学生可浏览的实验室路由（前缀 /lab，与实验室管理区分权限）
lab_public_router = APIRouter(prefix="/lab", tags=["实验室（学生浏览）"])

# 预约业务路由（前缀 /appointment）
router = APIRouter(prefix="/appointment", tags=["预约管理"])


# ============ 学生端：浏览实验室与设备（只读简单查询，暂留 api 层） ============

# 可预约实验室列表（status=1 启用），并统计每个实验室的设备总数
@lab_public_router.get("/available")
def available_labs(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),  # 登录即可
):
    labs = db.query(Lab).filter(Lab.status == 1).order_by(Lab.id).all()
    result = []
    for l in labs:
        # 统计该实验室下的设备数量
        cnt = db.query(Device).filter(Device.lab_id == l.id).count()
        result.append(
            {
                "id": l.id,
                "name": l.name,
                "code": l.code,
                "location": l.location,
                "capacity": l.capacity,
                "status": l.status,
                "device_count": cnt,
            }
        )
    return Response.success(data=result)


# 某实验室下的设备列表（支持 status 筛选）
@lab_public_router.get("/{lab_id}/devices")
def lab_devices(
    lab_id: int,
    status: int | None = Query(None, description="设备状态筛选"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    # 实验室是否存在
    lab = db.query(Lab).filter(Lab.id == lab_id).first()
    if not lab:
        raise HTTPException(status_code=404, detail="实验室不存在")
    query = db.query(Device).filter(Device.lab_id == lab_id)
    if status is not None:
        query = query.filter(Device.status == status)
    items = query.order_by(Device.id).all()
    return Response.success(
        data=[DeviceResponse.model_validate(d) for d in items]
    )


# ============ 预约业务：全部改为「调 service + 返回 Response」 ============

# 提交预约（学生）：校验和写入都在 service 里
@router.post("")
def create_appointment(
    data: AppointmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """提交预约：service 完成全部业务校验，失败会抛 BusinessException 统一返回"""
    result = appointment_service.create_reservation(
        db,
        user_id=current_user.id,
        lab_id=data.lab_id,
        device_id=data.device_id,
        appoint_date=data.appoint_date,
        start_time=data.start_time,
        end_time=data.end_time,
        purpose=data.purpose,
    )
    # dict → schema 的转换在 api 层完成（分层规范第 5、6 条）
    return Response.success(
        message="预约提交成功，等待审核",
        data=AppointmentResponse.model_validate(result),
    )


# 我的预约（学生，分页）：service 返回 (列表, 总数)
@router.get("/my")
def my_appointments(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    status: int | None = Query(None, description="状态筛选"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows, total = appointment_service.list_my_reservations(
        db, current_user.id, page, page_size, status
    )
    return Response.success(
        data={
            "list": [AppointmentResponse.model_validate(r) for r in rows],
            "total": total,
        }
    )


# 取消预约（学生）：仅本人、仅待审核/已通过可取消
@router.put("/{appt_id}/cancel")
def cancel_appointment(
    appt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = appointment_service.cancel_reservation(db, appt_id, current_user.id)
    return Response.success(
        message="已取消", data=AppointmentResponse.model_validate(result)
    )


# 全部预约列表（管理员，分页，支持 status 筛选）
@router.get("/list")
def list_appointments(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    status: int | None = Query(None, description="状态筛选"),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    rows, total = appointment_service.list_all_reservations(db, page, page_size, status)
    return Response.success(
        data={
            "list": [AppointmentResponse.model_validate(r) for r in rows],
            "total": total,
        }
    )


# 审核（管理员）：仅待审核可审核，结果只能是 通过(1) / 拒绝(2)
@router.put("/{appt_id}/review")
def review_appointment(
    appt_id: int,
    data: AppointmentReview,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    result = appointment_service.audit_reservation(db, appt_id, data.status)
    return Response.success(
        message="审核完成", data=AppointmentResponse.model_validate(result)
    )
