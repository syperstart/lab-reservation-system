# 预约业务层（service）：把「业务规则 + 数据库写入」从 api 层剥离出来
# 这是本项目第一个按 service 分层规范迁移的模块（示范），对应 api/appointment.py
#
# 分层规范在本文件里的体现：
#   1. 每个函数第一个参数固定是 db: Session（定时任务除外，用 SessionLocal 自己开）
#   2. 业务错误一律抛 BusinessException（不抛 HTTPException，HTTP 语义留给框架层）
#   3. add / commit / refresh 等写操作全部在 service 里完成
#   4. 返回拼装好的 dict / (list, total)，由 api 层转成 AppointmentResponse 返回前端
#   5. 命名：create_xxx / list_xxx / get_xxx / update_xxx / delete_xxx / 业务名（audit_reservation）

# datetime：判断「不能预约过去时间」、给定时任务算「预约结束时刻」
from datetime import datetime

# Session：给第一个参数做类型标注
from sqlalchemy.orm import Session

# SessionLocal：定时任务用（没有请求上下文，拿不到 Depends(get_db)）
from app.database import SessionLocal

# 模型：预约 + 关联的实验室 / 设备 / 学生
from app.model.lab import Lab
from app.model.device import Device
from app.model.appointment import Appointment
from app.model.user import User

# 业务异常：全局异常处理器会把它包成统一信封 {code, message, data} 返回
from common.exceptions import BusinessException


# 预约状态常量：集中定义，避免魔法数字散落各处
STATUS_PENDING = 0     # 待审核
STATUS_APPROVED = 1    # 已通过
STATUS_REJECTED = 2    # 已拒绝
STATUS_CANCELLED = 3   # 已取消
STATUS_ENDED = 4       # 已结束（结束时间过期后由定时任务自动置为此状态）


# ---- 内部工具：把一条预约记录拼成带名称的响应字典 ----
def build_appointment_data(db: Session, a: Appointment) -> dict:
    """根据预约记录，关联出 实验室 / 设备 / 学生 名称，返回可直接序列化的字典"""
    # 关联查实验室名称
    lab = db.query(Lab).filter(Lab.id == a.lab_id).first()
    # 设备是可选项（device_id 可空），有才查
    device = (
        db.query(Device).filter(Device.id == a.device_id).first()
        if a.device_id
        else None
    )
    # 关联查预约学生姓名
    user = db.query(User).filter(User.id == a.user_id).first()
    return {
        "id": a.id,
        "user_id": a.user_id,
        "lab_id": a.lab_id,
        "device_id": a.device_id,
        "appoint_date": a.appoint_date,
        "start_time": a.start_time,
        "end_time": a.end_time,
        "purpose": a.purpose,
        "status": a.status,
        "lab_name": lab.name if lab else None,
        "device_name": device.name if device else None,
        # 用户表真实姓名存在 real_name 字段，用这里做展示名
        "user_name": (user.real_name if user else None),
    }


# ---- 学生端：提交预约 ----
def create_reservation(
    db: Session,
    user_id: int,
    lab_id: int,
    device_id: int | None,
    appoint_date,
    start_time,
    end_time,
    purpose: str | None,
) -> dict:
    """提交预约：带全套业务校验（过去时间 / 顺序 / 实验室 / 设备 / 冲突），通过后写入并返回新纪录"""
    now = datetime.now()
    # 校验 1：不能预约过去的日期 / 时间
    if appoint_date < now.date():
        raise BusinessException("不能预约过去的日期", code=400)
    if appoint_date == now.date() and start_time <= now.time():
        raise BusinessException("不能预约过去的时间", code=400)
    # 校验 2：开始时间必须早于结束时间
    if start_time >= end_time:
        raise BusinessException("开始时间必须早于结束时间", code=400)

    # 校验 3：实验室必须存在且处于启用状态
    lab = db.query(Lab).filter(Lab.id == lab_id).first()
    if not lab:
        raise BusinessException("实验室不存在", code=400)
    if lab.status != 1:
        raise BusinessException("该实验室已停用，无法预约", code=400)

    # 校验 4：若指定设备，设备必须存在、属于该实验室且可用
    if device_id is not None:
        device = db.query(Device).filter(Device.id == device_id).first()
        if not device:
            raise BusinessException("设备不存在", code=400)
        if device.lab_id != lab_id:
            raise BusinessException("该设备不属于所选实验室", code=400)
        if device.status != 1:
            raise BusinessException("该设备不可用", code=400)

    # 校验 5：时间段冲突（同实验室或同设备，区间重叠，只看未结束的有效预约）
    # 区间重叠判定：对方开始 < 我方结束 且 对方结束 > 我方开始
    existing = (
        db.query(Appointment)
        .filter(
            Appointment.appoint_date == appoint_date,
            # 只查 待审核(0) / 已通过(1)；已拒绝 / 已取消 / 已结束 不占时段
            Appointment.status.in_([STATUS_PENDING, STATUS_APPROVED]),
        )
        .all()
    )
    for a in existing:
        overlap = a.start_time < end_time and a.end_time > start_time
        if not overlap:
            continue
        # 同一实验室，或指定了同一台设备 → 冲突
        if a.lab_id == lab_id or (device_id is not None and a.device_id == device_id):
            raise BusinessException("该时间段与已有预约冲突，请更换时间", code=400)

    # 全部校验通过 → 创建预约，初始状态 待审核(0)
    appt = Appointment(
        user_id=user_id,
        lab_id=lab_id,
        device_id=device_id,
        appoint_date=appoint_date,
        start_time=start_time,
        end_time=end_time,
        purpose=purpose,
        status=STATUS_PENDING,
    )
    # 数据库写入在 service 里完成（分层规范第 4 条）
    db.add(appt)
    db.commit()
    db.refresh(appt)
    # 返回拼好名称的字典，api 层直接转 schema
    return build_appointment_data(db, appt)


# ---- 学生端：我的预约列表 ----
def list_my_reservations(
    db: Session,
    user_id: int,
    page: int,
    page_size: int,
    status: int | None,
):
    """分页查询某个学生自己的预约；返回 (列表字典, 总数)"""
    # 只查本人预约
    query = db.query(Appointment).filter(Appointment.user_id == user_id)
    # 状态筛选（None=不过滤，查全部）
    if status is not None:
        query = query.filter(Appointment.status == status)
    # 总数（给前端分页组件）
    total = query.count()
    # 分页取数据：按 id 倒序（新预约在前）
    items = (
        query.order_by(Appointment.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    # 每条都拼上实验室 / 设备 / 学生名称
    return [build_appointment_data(db, a) for a in items], total


# ---- 学生端：取消预约 ----
def cancel_reservation(db: Session, reservation_id: int, user_id: int) -> dict:
    """取消预约：仅本人、仅 待审核/已通过 状态可取消 → 已取消(3)"""
    a = db.query(Appointment).filter(Appointment.id == reservation_id).first()
    # 预约不存在：业务错误抛 BusinessException（分层规范：不抛 HTTPException）
    if not a:
        raise BusinessException("预约不存在", code=404)
    # 只能取消自己的预约
    if a.user_id != user_id:
        raise BusinessException("只能取消自己的预约", code=400)
    # 状态机：只有 待审核(0) / 已通过(1) 可取消 → 已取消(3)
    if a.status not in (STATUS_PENDING, STATUS_APPROVED):
        raise BusinessException("当前状态不可取消", code=400)
    a.status = STATUS_CANCELLED
    db.commit()
    db.refresh(a)
    return build_appointment_data(db, a)


# ---- 管理员端：全部预约列表 ----
def list_all_reservations(
    db: Session,
    page: int,
    page_size: int,
    status: int | None,
):
    """管理员分页查询所有预约；返回 (列表字典, 总数)"""
    query = db.query(Appointment)
    if status is not None:
        query = query.filter(Appointment.status == status)
    total = query.count()
    items = (
        query.order_by(Appointment.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return [build_appointment_data(db, a) for a in items], total


# ---- 管理员端：审核预约 ----
def audit_reservation(db: Session, reservation_id: int, status: int) -> dict:
    """审核预约：仅 待审核(0) 可审核，结果只能是 通过(1) / 拒绝(2)"""
    a = db.query(Appointment).filter(Appointment.id == reservation_id).first()
    if not a:
        raise BusinessException("预约不存在", code=404)
    # 状态机：只有待审核(0) 能审核
    if a.status != STATUS_PENDING:
        raise BusinessException("只有待审核的预约可以审核", code=400)
    # 审核结果只能是 1 通过 或 2 拒绝
    if status not in (STATUS_APPROVED, STATUS_REJECTED):
        raise BusinessException("审核结果只能是 1(通过) 或 2(拒绝)", code=400)
    a.status = status
    db.commit()
    db.refresh(a)
    return build_appointment_data(db, a)


# ---- 定时任务：过期预约自动结束 ----
def exp_end_pending_reservations() -> int:
    """定时任务：把「结束时间已过」但仍处于 待审核(0)/已通过(1) 的预约自动置为 已结束(4)。

    定时任务没有请求上下文，拿不到 Depends(get_db)，所以按分层规范用 SessionLocal 自己开会话。
    返回本次自动结束的条数，方便调用方打日志 / 监控。
    （真正的周期调度以后接 APScheduler 之类的框架时，把这个函数挂上去即可。）
    """
    db = SessionLocal()
    try:
        now = datetime.now()
        # 先把还处于 待审核(0) / 已通过(1) 的预约全部查出（数据量小，直接全查再逐条判断）
        rows = (
            db.query(Appointment)
            .filter(Appointment.status.in_([STATUS_PENDING, STATUS_APPROVED]))
            .all()
        )
        # 结束时刻 = 预约日期 + 结束时间（date + time 拼成 datetime 再比较）
        ended = 0
        for a in rows:
            end_dt = datetime.combine(a.appoint_date, a.end_time)
            if end_dt < now:
                a.status = STATUS_ENDED
                ended += 1
        # 有变更才提交，避免无意义 commit
        if ended > 0:
            db.commit()
        return ended
    finally:
        # 无论成功失败都关闭会话，把连接还回连接池
        db.close()
