# 从 Python 标准库导入 Path，用来拼出 .env 文件的绝对路径
from pathlib import Path

# 从 pydantic-settings 导入两个工具：
# BaseSettings = 配置类的父类；SettingsConfigDict = 告诉它去哪里读配置
from pydantic_settings import BaseSettings, SettingsConfigDict

# __file__ 是当前 config.py 的路径，.resolve() 把它变成完整绝对路径
# 第一次 .parent 得到 app 目录，第二次 .parent 得到 backend 根目录（.env 就在这里）
BASE_DIR = Path(__file__).resolve().parent.parent

# 定义配置类：继承 BaseSettings 后，会自动用 .env / 环境变量里同名的项给下面字段赋值
class Settings(BaseSettings):
    # ---------- 一、API 接口相关配置 ----------
    # 接口标题；等号右边是默认值，.env 里写了就优先用 .env 的值
    API_TITLE: str = "智能预约系统 API"

    # 所有业务接口的统一前缀
    API_PREFIX: str = "/api/v1"

    # 以后调用第三方接口用的 Key，现在先留空字符串
    THIRD_PARTY_API_KEY: str = ""

    # ---------- 二、JWT 登录令牌配置 ----------
    # 签名密钥：给登录令牌签名用；这个默认值只适合本地开发，真值从 .env 读取
    SECRET_KEY: str = "dev-only-secret-key-please-change"

    # 签名算法：HS256 表示用同一把密钥签名和校验
    ALGORITHM: str = "HS256"

    # 访问令牌有效期，单位分钟；写成 int，pydantic 会自动把 .env 的字符串转成整数
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # 刷新令牌有效期，单位天；以后做「免重复登录」时用
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ---------- 视频教程命名兼容（只读别名，不新增 .env 变量） ----------
    # 教程代码里写的是 settings.JWT_SECRET_KEY / JWT_ALGORITHM / JWT_EXPIRE_HOURS，
    # 这里用 @property 把它们映射到本项目 .env 里已经存在的字段，
    # 好处：照抄教程代码也能跑，同时不会出现「两把密钥 / 两套有效期」
    @property
    def JWT_SECRET_KEY(self) -> str:
        # 对应 .env 里的 SECRET_KEY
        return self.SECRET_KEY

    @property
    def JWT_ALGORITHM(self) -> str:
        # 对应 .env 里的 ALGORITHM
        return self.ALGORITHM

    @property
    def JWT_EXPIRE_HOURS(self) -> float:
        # 教程按「小时」算，本项目 .env 按「分钟」存，这里换算一下
        # 例如 60 分钟 → 1.0 小时；30 分钟 → 0.5 小时
        return self.ACCESS_TOKEN_EXPIRE_MINUTES / 60

    # ---------- 三、数据库配置 ----------
    # ★ 最关键的一行：数据库连接串
    # database.py 里就是 create_engine(settings.DATABASE_URL) 用它连上 MySQL
    DATABASE_URL: str = "mysql+pymysql://root:123456@127.0.0.1:3306/lab-agent?charset=utf8mb4"

    # ---------- 四、文件上传配置 ----------
    # 上传文件根目录：拼上 BASE_DIR 变成绝对路径（backend/uploads），
    # 和 .env 的绝对路径思路一致——无论从哪个目录启动服务，文件都存到固定位置
    UPLOAD_DIR: str = str(BASE_DIR / "uploads")

    # 单个文件大小上限，单位 MB；超过就拒绝上传
    MAX_UPLOAD_SIZE_MB: int = 5

    # 允许上传的扩展名白名单（小写、逗号分隔），不在名单里的一律拒绝
    ALLOWED_EXTENSIONS: str = "jpg,jpeg,png,gif,webp"

    # ---------- 五、AI 助手（大模型）配置 ----------
    # 大模型的 API Key：真值只放 .env（.env 已被 .gitignore 忽略，绝不提交）；
    # 缺失时 service 层会抛「AI 服务未配置」
    LM_API_KEY: str = ""

    # 大模型服务的接口地址：DeepSeek 官方兼容 OpenAI 接口规范，base_url 就写这个
    LM_BASE_URL: str = "https://api.deepseek.com"

    # 使用的模型名：deepseek-chat 是 DeepSeek 的通用对话模型
    LM_MODEL: str = "deepseek-chat"

    # ---------- 六、RAG 知识库配置 ----------
    # 答疑知识库目录：存放 Markdown 问答文件，由 app/services/kb_service.py 加载
    KB_DIR: str = str(BASE_DIR / "knowledge")

    # ChromaDB 集合名：本项目只有一个答疑集合
    KB_COLLECTION: str = "knowledge_base"

    # 每次语义检索返回的知识块条数（拼进大模型上下文）
    KB_TOP_K: int = 5

    # model_config 是 pydantic-settings 的固定写法，用来配置「去哪读、怎么读」
    model_config = SettingsConfigDict(
        # 指定 .env 的绝对路径：这样无论从哪个目录启动服务，都能找到这个文件
        env_file=str(BASE_DIR / ".env"),
        # 用 UTF-8 编码读取，中文值和中文注释才不会乱码
        env_file_encoding="utf-8",
        # 环境变量名不区分大小写，DATABASE_URL 和 database_url 都能认
        case_sensitive=False,
        # .env 里如果有这里没定义的多余配置项，直接忽略而不报错
        extra="ignore",
    )

# 创建全局唯一的配置对象；其它文件统一写 from app.config import settings 来用
settings = Settings()
