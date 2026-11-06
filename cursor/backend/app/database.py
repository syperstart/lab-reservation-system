# 从 SQLAlchemy 的 orm 模块导入 4 个工具：
# sessionmaker=会话工厂，DeclarativeBase=声明式基类，Mapped=字段类型标注，mapped_column=定义一列
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Mapped, mapped_column

# 从 SQLAlchemy 导入：create_engine=创建数据库引擎；DateTime=数据库里的日期时间列类型
from sqlalchemy import create_engine, DateTime

# 从 Python 标准库导入 datetime，用来给「创建时间 / 更新时间」填默认值
from datetime import datetime

# 导入 config.py 里读好 .env 的配置对象，settings.DATABASE_URL 就是连接串
from app.config import settings

# 创建「引擎」：引擎负责管理数据库连接池，真正执行 SQL 都靠它
# pool_pre_ping=True 表示每次取连接前先测试一下，避免拿到已断开的旧连接
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)

# 创建「会话工厂」：每次调用 SessionLocal() 都会得到一个独立的数据库会话
# bind=engine 指定它使用上面那个引擎；autoflush=False 避免查询前自动偷偷写入数据
SessionLocal = sessionmaker(bind=engine, autoflush=False)

# 给 FastAPI 用的「依赖注入」函数：接口里写 Depends(get_db) 就能拿到一个会话
def get_db():
    # 从会话工厂取出一个会话对象
    db = SessionLocal()
    try:
        # yield 把会话交给接口函数使用，接口的代码就在这个位置执行
        yield db
    finally:
        # 不管接口成功还是报错，最后都关闭会话，把连接还回连接池
        db.close()

# 所有数据表模型都要继承的「公共父类」（参考图一、图二的写法）
class Base(DeclarativeBase):
    # 主键 ID：凡是继承 Base 的表，都会自动带上这一列
    # primary_key=True 设为主键，autoincrement=True 表示自增，comment 是写进数据库的注释
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="主键ID")

    # 创建时间：插入新数据时自动填当前时间
    # 注意 default=datetime.now 不要加括号，加括号会在程序启动时就把时间定死
    create_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="创建时间")

    # 更新时间：插入时填当前时间，之后每次修改这条数据也会自动刷新
    # onupdate 就是「更新时自动执行」的意思
    update_time: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间"
    )

# 建表函数：把继承 Base 的模型，在数据库里真正创建成表
def init_db():
    # 在函数内部导入各模型：只有导入了这些类，SQLAlchemy 才知道要建对应的表
    # noqa: F401 是告诉代码检查工具「这个导入看起来没用到，但其实是有意为之」
    from app.model.user import User  # noqa: F401
    # 实验室 / 设备 / 预约 三个新业务表
    from app.model.lab import Lab  # noqa: F401
    from app.model.device import Device  # noqa: F401
    from app.model.appointment import Appointment  # noqa: F401

    # create_all 只创建「还不存在的表」，已存在的表不会被覆盖、也不会删数据
    Base.metadata.create_all(bind=engine)
