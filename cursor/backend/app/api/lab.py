# 实验室管理接口：全部需要管理员权限
# 路径前缀写 /lab，总路由 api/__init__.py 再统一加 /api → 完整路径 /api/lab/...

# APIRouter=路由容器；Depends=依赖注入；Query=声明查询参数；HTTPException=主动返回 HTTP 错误
from fastapi import APIRouter, Depends, Query, HTTPException

# Session=数据库会话类型标注
from sqlalchemy.orm import Session

# or_=SQL 里的「或」条件，用于关键字同时匹配名称和编号
from sqlalchemy import or_

# 登录校验依赖 + 管理员权限依赖
from app.dependencies.auth import get_current_user
from app.dependencies.permission import require_admin

# 模型与用户模型
from app.model.user import User
from app.model.lab import Lab
from app.model.device import Device

# 实验室相关的请求 / 响应模型
from app.schemas.lab import LabResponse, LabCreate, LabUpdate

# 数据库会话依赖 + 统一响应 + 业务异常
from app.database import get_db
from common.exceptions import BusinessException
from common.response import Response

# 子路由前缀 /lab（总路由再套 /api）
router = APIRouter(prefix="/lab", tags=["实验室管理"])


# 分页列表：支持 page / page_size / keyword（名称或编号模糊）/ status 筛选
@router.get("/list")
def list_labs(
    page: int = Query(1, ge=1, description="页码，从1开始"),
    page_size: int = Query(10, ge=1, le=100, description="每页条数"),
    keyword: str | None = Query(None, description="关键字：匹配名称或编号"),
    status: int | None = Query(None, description="状态筛选：1启用 0停用"),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),  # 管理员专属
):
    # 构建基础查询
    query = db.query(Lab)
    # 关键字模糊匹配名称或编号
    if keyword:
        kw = f"%{keyword}%"
        query = query.filter(or_(Lab.name.contains(kw), Lab.code.contains(kw)))
    # 状态筛选（status=0 也是有效值，用 is not None 判断）
    if status is not None:
        query = query.filter(Lab.status == status)
    # 总数（用于分页组件）
    total = query.count()
    # 分页取数据：按 id 倒序（新数据在前），跳过前面页、取本页
    items = (
        query.order_by(Lab.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return Response.success(
        data={
            "list": [LabResponse.model_validate(x) for x in items],
            "total": total,
        }
    )


# 下拉选项：返回启用中的实验室（id + name），给新增设备等场景用
@router.get("/options")
def lab_options(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    labs = db.query(Lab).filter(Lab.status == 1).order_by(Lab.id).all()
    return Response.success(
        data=[{"id": l.id, "name": l.name} for l in labs]
    )


# 详情：不存在返回 404
@router.get("/{lab_id}")
def get_lab(
    lab_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    lab = db.query(Lab).filter(Lab.id == lab_id).first()
    if not lab:
        raise HTTPException(status_code=404, detail="实验室不存在")
    return Response.success(data=LabResponse.model_validate(lab))


# 新增：校验编号唯一，重复抛业务异常
@router.post("")
def create_lab(
    data: LabCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    # 编号唯一校验（模型层 unique=True 是第二道保险）
    exists = db.query(Lab).filter(Lab.code == data.code.strip()).first()
    if exists:
        raise BusinessException("实验室编号已存在", code=400)
    # 创建并写入数据库
    lab = Lab(
        name=data.name.strip(),
        code=data.code.strip(),
        location=data.location,
        capacity=data.capacity,
        description=data.description,
        status=data.status,
    )
    db.add(lab)
    db.commit()
    db.refresh(lab)
    return Response.success(message="创建成功", data=LabResponse.model_validate(lab))


# 修改：校验编号唯一（排除自身）
@router.put("/{lab_id}")
def update_lab(
    lab_id: int,
    data: LabUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    lab = db.query(Lab).filter(Lab.id == lab_id).first()
    if not lab:
        raise HTTPException(status_code=404, detail="实验室不存在")
    # 编号若修改，需保证不与别的实验室重复
    if data.code is not None:
        dup = (
            db.query(Lab)
            .filter(Lab.code == data.code.strip(), Lab.id != lab_id)
            .first()
        )
        if dup:
            raise BusinessException("实验室编号已存在", code=400)
        lab.code = data.code.strip()
    # 其余字段按需更新
    if data.name is not None:
        lab.name = data.name.strip()
    if data.location is not None:
        lab.location = data.location
    if data.capacity is not None:
        lab.capacity = data.capacity
    if data.description is not None:
        lab.description = data.description
    if data.status is not None:
        lab.status = data.status
    db.commit()
    db.refresh(lab)
    return Response.success(message="更新成功", data=LabResponse.model_validate(lab))


# 删除：若实验室下仍有设备，拒绝删除并提示
@router.delete("/{lab_id}")
def delete_lab(
    lab_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    lab = db.query(Lab).filter(Lab.id == lab_id).first()
    if not lab:
        raise HTTPException(status_code=404, detail="实验室不存在")
    # 检查是否还有设备挂在下面
    has_device = db.query(Device).filter(Device.lab_id == lab_id).first()
    if has_device:
        raise BusinessException("请先移除该实验室下的设备", code=400)
    db.delete(lab)
    db.commit()
    return Response.success(message="删除成功")
