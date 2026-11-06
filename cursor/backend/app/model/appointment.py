# 预约表模型：一个类对应数据库里的一张 appointment 表
from app.database import Base

# 导入 ORM 字段工具与列类型
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, ForeignKey, Date, Time

# 导入日期 / 时间类型（Python 标准库），用来给字段做类型标注
from datetime import date, time


class Appointment(Base):
    """预约表"""

    # 数据库中真正的表名
    __tablename__ = "appointment"

    # 预约学生：外键指向 user.id，非空
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id"), comment="预约学生", nullable=False
    )

    # 实验室：外键指向 lab.id，非空
    lab_id: Mapped[int] = mapped_column(
        ForeignKey("lab.id"), comment="实验室", nullable=False
    )

    # 设备：外键指向 device.id，可空（预约实验室但不指定具体设备）
    device_id: Mapped[int | None] = mapped_column(
        ForeignKey("device.id"), comment="设备，可空"
    )

    # 预约日期：非空
    appoint_date: Mapped[date] = mapped_column(Date, comment="预约日期", nullable=False)

    # 开始时间：非空
    start_time: Mapped[time] = mapped_column(Time, comment="开始时间", nullable=False)

    # 结束时间：非空
    end_time: Mapped[time] = mapped_column(Time, comment="结束时间", nullable=False)

    # 用途：可空
    purpose: Mapped[str | None] = mapped_column(String(255), comment="用途")

    # 状态：0=待审核，1=已通过，2=已拒绝，3=已取消；默认待审核
    status: Mapped[int] = mapped_column(
        Integer, default=0, comment="状态: 0-待审核 1-已通过 2-已拒绝 3-已取消"
    )
