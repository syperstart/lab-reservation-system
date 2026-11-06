# 实验室表模型：一个类对应数据库里的一张 lab 表
# 继承 Base 后会自动带上 id / create_time / update_time 三列（见 app/database.py）
from app.database import Base

# 导入 ORM 字段工具：Mapped 标注 Python 类型，mapped_column 定义数据库列
from sqlalchemy.orm import Mapped, mapped_column

# 导入列类型：String=变长字符串，Integer=整数
from sqlalchemy import String, Integer


class Lab(Base):
    """实验室表"""

    # 数据库中真正的表名
    __tablename__ = "lab"

    # 实验室名称：非空
    name: Mapped[str] = mapped_column(String(100), comment="实验室名称", nullable=False)

    # 实验室编号：非空且唯一（业务上不允许重复，模型层加 unique=True 双保险）
    code: Mapped[str] = mapped_column(String(50), comment="编号", nullable=False, unique=True)

    # 位置：可空
    location: Mapped[str | None] = mapped_column(String(100), comment="位置")

    # 可容纳人数：可空（整数）
    capacity: Mapped[int | None] = mapped_column(Integer, comment="可容纳人数")

    # 描述：可空
    description: Mapped[str | None] = mapped_column(String(255), comment="描述")

    # 状态：1=启用，0=停用；默认启用
    status: Mapped[int] = mapped_column(Integer, default=1, comment="状态: 1-启用 0-停用")
