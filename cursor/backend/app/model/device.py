# 设备表模型：一个类对应数据库里的一张 device 表
from app.database import Base

# 导入 ORM 字段工具与列类型
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, ForeignKey


class Device(Base):
    """设备表"""

    # 数据库中真正的表名
    __tablename__ = "device"

    # 所属实验室：外键指向 lab.id，非空（删实验室时若仍有设备会在接口层拦截，不会级联删除）
    lab_id: Mapped[int] = mapped_column(
        ForeignKey("lab.id"), comment="所属实验室", nullable=False
    )

    # 设备名称：非空
    name: Mapped[str] = mapped_column(String(100), comment="设备名称", nullable=False)

    # 图片 URL：可空，前端没上传时显示占位图（不出现破图）
    image: Mapped[str | None] = mapped_column(String(255), comment="图片URL", nullable=True)

    # 型号规格：可空
    model: Mapped[str | None] = mapped_column(String(100), comment="型号规格")

    # 数量：默认 1，至少 1 台（界面用 el-input-number 限制最小值）
    quantity: Mapped[int] = mapped_column(Integer, default=1, comment="数量", nullable=False)

    # 状态：1=正常，0=维修；默认可用（预约接口里 status!=1 视为不可用）
    status: Mapped[int] = mapped_column(Integer, default=1, comment="状态: 1-正常 0-维修")

    # 说明：可空
    description: Mapped[str | None] = mapped_column(String(255), comment="说明")
