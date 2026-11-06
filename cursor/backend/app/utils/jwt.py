# JWT 工具文件：负责「生成登录令牌」和「校验并解析登录令牌」
# 视频教程里这个文件叫 app/utils/jwt.py，生成函数叫 create_access_token；
# 校验函数 decode_access_token 是做登录依赖时补上的（见 DEVELOPMENT.md 第 19 步）

# 从标准库导入三个时间工具：
# datetime 取当前时间，timedelta 算过期时间，timezone.utc 保证用的是 UTC 时间
from datetime import datetime, timedelta, timezone

# 导入 PyJWT 库：用它把用户数据签名成一串 token 字符串
import jwt

# 导入配置对象：密钥、算法、有效期全部从 .env 读取，不写死在代码里
from app.config import settings


def create_access_token(user_id: int) -> str:
    """创建JWT token：把用户 id 装进令牌，并按配置的有效期设置过期时间"""
    # 过期时刻 = 当前 UTC 时间 + 配置的有效小时数
    # 修正 1：视频里写 datetime.now()（本地时间），PyJWT 会把它当成 UTC 计算，
    # 在国内会平白多出 8 小时；这里改用 timezone.utc，并配合上面导入的 timedelta
    expire = datetime.now(timezone.utc) + timedelta(hours=settings.JWT_EXPIRE_HOURS)

    # 载荷 payload：要写进 token 里的数据
    # 修正 2：视频里写的是 "expire"，但 PyJWT 只认标准字段 "exp"，
    # 用 "expire" 的话令牌永远不会过期，所以这里改成 "exp"
    payload = {"user_id": user_id, "exp": expire}

    # 用 .env 里的密钥和算法签名，返回字符串形式的 token
    # settings.JWT_SECRET_KEY / JWT_ALGORITHM 是 config.py 里做的兼容别名，
    # 实际指向 .env 的 SECRET_KEY / ALGORITHM
    return jwt.encode(
        payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )


def decode_access_token(token: str) -> dict:
    """校验 JWT token 并返回里面的载荷字典；令牌无效或过期会直接抛异常"""
    # jwt.decode 用同一把密钥 + 同一个算法验签，并自动检查 exp 是否过期
    # 过期抛 ExpiredSignatureError、签名错抛 InvalidSignatureError，
    # 它们都是 Exception 的子类，所以 dependencies/auth.py 里的 except Exception
    # 能把所有失败统一转成 401「登录已失效，请重新登录」
    return jwt.decode(
        token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
    )
