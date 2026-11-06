# 密码工具：用 bcrypt 做密码哈希与校验
import bcrypt


def hash_password(password: str) -> str:
    """把明文密码变成 bcrypt 哈希字符串（注册 / 改密码时用）"""
    # 修正：原写法把 bcrypt.gensalt() 放进了 str.encode() 的第二个参数，
    # 那个位置是「编码错误处理方式」，只接受字符串，传 bytes 会报 TypeError
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed_password: str) -> bool:
    """校验密码：支持 bcrypt 哈希，同时兼容数据库里现存的明文示例数据"""
    # 数据库里没存密码，直接判失败
    if not hashed_password:
        return False

    # lab-agent.user 里目前 3 条示例用户还是明文（admin / student01 / student02）。
    # bcrypt 哈希都以 $2a$ / $2b$ / $2y$ 开头，不是哈希就按明文比较：
    # 这样现有示例账号仍能登录，以后把密码换成哈希也不用改这里
    if not hashed_password.startswith(("$2a$", "$2b$", "$2y$")):
        return password == hashed_password

    # 标准 bcrypt 校验：checkpw 需要两个参数，且都要是 bytes
    # 修正：原写法只传了一个参数、也没用到 hashed_password，还会误传 gensalt()
    return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))
