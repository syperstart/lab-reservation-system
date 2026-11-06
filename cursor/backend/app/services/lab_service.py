# 实验室查询业务层（service）：专供 AI 助手「工具调用」使用的只读查询
# 与 api/lab.py 的差异：api 层面向管理员管理界面（分页 / 增删改查），
# 这里面向 AI 工具（全量、只读、返回精简字段）。
#
# 分层规范：
#   1. 第一个参数固定 db: Session
#   2. 业务错误一律抛 BusinessException（不抛 HTTPException）
#   3. 只读查询，绝不写数据库

# Session：给第一个参数做类型标注
from sqlalchemy.orm import Session

# or_：关键字筛选时「名称或编号」任一匹配
from sqlalchemy import or_

# 模型：实验室 + 设备
from app.model.lab import Lab
from app.model.device import Device

# 业务异常：全局异常处理器会把它包成统一信封 {code, message, data} 返回
from common.exceptions import BusinessException


# 单条实验室 → 可序列化字典（AI 工具返回给大模型看的字段）
def build_lab_data(l: Lab) -> dict:
    """把 Lab ORM 对象转成字典，只保留助手回答需要的关键字段"""
    return {
        "id": l.id,
        "name": l.name,
        "location": l.location,
        "capacity": l.capacity,
        # 注意：lab 表目前没有「开放时间」两列，这里先返回 None，绝不编造；
        # 等以后模型增加 open_start / open_end 字段，再改成真实值
        "open_start": None,
        "open_end": None,
        "status": l.status,  # 1=启用 0=停用
    }


def list_labs(db: Session, keyword: str | None = None) -> list[dict]:
    """查询启用中的实验室列表（可选：按名称/编号关键字模糊筛选）"""
    # 只查启用中的实验室（停用的学生也看不到）
    query = db.query(Lab).filter(Lab.status == 1)
    # 关键字模糊匹配名称或编号（与 api/lab.py 的筛选逻辑一致）
    if keyword and keyword.strip():
        kw = f"%{keyword.strip()}%"
        query = query.filter(or_(Lab.name.contains(kw), Lab.code.contains(kw)))
    # 按 id 正序返回，保证结果稳定
    labs = query.order_by(Lab.id).all()
    return [build_lab_data(l) for l in labs]


def get_lab(db: Session, lab_id: int) -> dict:
    """查询单个实验室详情；不存在抛 BusinessException（code=404）"""
    lab = db.query(Lab).filter(Lab.id == lab_id).first()
    if not lab:
        raise BusinessException("实验室不存在", code=404)
    return build_lab_data(lab)


def list_lab_devices(db: Session, lab_id: int, status: int | None = None) -> list[dict]:
    """查询某个实验室下的设备列表（可选：按状态筛选，1=正常 0=维修）"""
    # 先确认实验室存在：给模型一个明确错误，比返回空列表更友好
    lab = db.query(Lab).filter(Lab.id == lab_id).first()
    if not lab:
        raise BusinessException("实验室不存在", code=404)
    # 查该实验室的设备；status 用 is not None 判断（status=0 也是有效筛选值）
    query = db.query(Device).filter(Device.lab_id == lab_id)
    if status is not None:
        query = query.filter(Device.status == status)
    devices = query.order_by(Device.id).all()
    return [
        {
            "id": d.id,
            "name": d.name,
            "model": d.model,      # 型号规格（可空）
            "quantity": d.quantity,  # 数量
            "status": d.status,      # 1=正常 0=维修
        }
        for d in devices
    ]
