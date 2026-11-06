# 设备列表管理接口：全部需要管理员权限
# 路径前缀写 /device，总路由再统一加 /api → /api/device/...

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

# 登录校验 + 管理员权限依赖
from app.dependencies.auth import get_current_user
from app.dependencies.permission import require_admin

# 模型
from app.model.user import User
from app.model.lab import Lab
from app.model.device import Device
from app.model.appointment import Appointment  # 删除时检查关联预约

# 设备请求 / 响应模型
from app.schemas.device import DeviceResponse, DeviceCreate, DeviceUpdate

# 数据库会话 + 统一响应 + 业务异常
from app.database import get_db
from common.exceptions import BusinessException
from common.response import Response

router = APIRouter(prefix="/device", tags=["设备列表管理"])


# 分页列表：支持 lab_id / name(模糊) / status 筛选
@router.get("/list")
def list_devices(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    lab_id: int | None = Query(None, description="按实验室筛选"),
    name: str | None = Query(None, description="设备名称模糊匹配"),
    status: int | None = Query(None, description="状态筛选：1正常 0维修"),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    query = db.query(Device)
    if lab_id is not None:
        query = query.filter(Device.lab_id == lab_id)
    # 关键字只匹配设备名称（按需求，去掉了原编号 code 字段）
    if name:
        kw = f"%{name}%"
        query = query.filter(Device.name.contains(kw))
    if status is not None:
        query = query.filter(Device.status == status)
    total = query.count()
    items = (
        query.order_by(Device.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    # 关联出实验室名称，避免前端二次请求
    result = []
    for d in items:
        lab = db.query(Lab).filter(Lab.id == d.lab_id).first()
        r = DeviceResponse.model_validate(d)
        r.lab_name = lab.name if lab else None
        result.append(r)
    return Response.success(data={"list": result, "total": total})


# 详情：带实验室名称
@router.get("/{device_id}")
def get_device(
    device_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    d = db.query(Device).filter(Device.id == device_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="设备不存在")
    lab = db.query(Lab).filter(Lab.id == d.lab_id).first()
    r = DeviceResponse.model_validate(d)
    r.lab_name = lab.name if lab else None
    return Response.success(data=r)


# 新增：校验实验室存在即可（设备不再有编号唯一约束）
@router.post("")
def create_device(
    data: DeviceCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    # 外键存在性校验（不依赖数据库报错）
    lab = db.query(Lab).filter(Lab.id == data.lab_id).first()
    if not lab:
        raise BusinessException("所属实验室不存在", code=400)
    dev = Device(
        lab_id=data.lab_id,
        name=data.name.strip(),
        image=data.image,
        model=data.model,
        quantity=data.quantity,
        status=data.status,
        description=data.description,
    )
    db.add(dev)
    db.commit()
    db.refresh(dev)
    r = DeviceResponse.model_validate(dev)
    r.lab_name = lab.name
    return Response.success(message="创建成功", data=r)


# 修改：校验实验室存在（如有修改），更新各字段
@router.put("/{device_id}")
def update_device(
    device_id: int,
    data: DeviceUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    d = db.query(Device).filter(Device.id == device_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="设备不存在")
    # 实验室若改，需保证存在
    if data.lab_id is not None:
        lab = db.query(Lab).filter(Lab.id == data.lab_id).first()
        if not lab:
            raise BusinessException("所属实验室不存在", code=400)
        d.lab_id = data.lab_id
    if data.name is not None:
        d.name = data.name.strip()
    if data.image is not None:
        d.image = data.image
    if data.model is not None:
        d.model = data.model
    if data.quantity is not None:
        d.quantity = data.quantity
    if data.status is not None:
        d.status = data.status
    if data.description is not None:
        d.description = data.description
    db.commit()
    db.refresh(d)
    lab = db.query(Lab).filter(Lab.id == d.lab_id).first()
    r = DeviceResponse.model_validate(d)
    r.lab_name = lab.name if lab else None
    return Response.success(message="更新成功", data=r)


# 删除：若存在未完成的预约（待审核/已通过），拒绝删除
@router.delete("/{device_id}")
def delete_device(
    device_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    d = db.query(Device).filter(Device.id == device_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="设备不存在")
    # 查是否存在未完成的预约（状态 0 待审核 / 1 已通过）
    has_appt = (
        db.query(Appointment)
        .filter(Appointment.device_id == device_id, Appointment.status.in_([0, 1]))
        .first()
    )
    if has_appt:
        raise BusinessException("该设备存在未完成的预约，无法删除", code=400)
    db.delete(d)
    db.commit()
    return Response.success(message="删除成功")
