# 导入公共基类：继承 Base 后，会自动拥有 id、create_time、update_time 三列
from app.database import Base

# 导入 ORM 的字段工具：Mapped 声明 Python 类型，mapped_column 声明数据库里的列
from sqlalchemy.orm import Mapped, mapped_column

# 导入 String，对应 MySQL 的 VARCHAR(长度)
from sqlalchemy import String

# 定义「用户表」模型：一个类就对应数据库里的一张表
class User(Base):
    # 数据库中真正的表名（参考图三，用 user）
    __tablename__ = "user"

    # 表级备注，会写进 MySQL 的 CREATE TABLE ... COMMENT='用户信息表'
    __table_args__ = {"comment": "用户信息表"}

    # 登录账号：String(50)=VARCHAR(50)，nullable=False=不允许为空
    username: Mapped[str] = mapped_column(String(50), comment="账号", nullable=False)

    # 真实姓名 / 昵称，同样不允许为空
    real_name: Mapped[str] = mapped_column(String(50), comment="名称", nullable=False)

    # 登录密码：参考图三存的是字符串；正式项目应存哈希值并把长度改成 255
    password: Mapped[str] = mapped_column(String(255), comment="密码", nullable=False)

    # 角色：student=学生，admin=管理员；用注释把取值含义写清楚
    role: Mapped[str] = mapped_column(
        String(50), comment="角色: student-学生 admin-管理员", nullable=False
    )

    # 邮箱：类型写成 str | None 表示「可以为空」，SQLAlchemy 会自动设 nullable=True
    email: Mapped[str | None] = mapped_column(String(50), comment="邮箱")

    # 手机号，允许为空
    phone: Mapped[str | None] = mapped_column(String(50), comment="手机号")

    # 头像地址，允许为空；长度给到 255，因为头像 URL 形如
    # /uploads/avatar/2026/11/05/<uuid>.png，超过 50 会写入失败
    avatar: Mapped[str | None] = mapped_column(String(255), comment="头像")

    # 状态：1=正常，0=禁用；Mapped[int] 会自动推断出 INTEGER 类型
    status: Mapped[int] = mapped_column(default=1, comment="状态: 0-禁用 1-正常")
