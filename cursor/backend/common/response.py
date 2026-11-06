# 统一响应格式工具
# 作用：以后所有接口都返回同一个「外壳」（code / message / data），
#       前端拿到后只要看 code 就知道成功还是失败，不用每个接口各写各的格式。

# typing.Any 表示「任意类型」：data 里可以放 dict、list、字符串……什么都行
from typing import Any

# pydantic 的 BaseModel 是 FastAPI 用来做数据校验和自动生成接口的基类
from pydantic import BaseModel


class Response(BaseModel):
    """统一封装的响应格式（前端拿到的 JSON 都长这个样子）"""

    # 业务状态码：200 代表成功，其它数字代表不同类型的错误
    code: int

    # 给前端看的一句话提示，比如「登录成功」「请求失败」
    message: str

    # 真正要返回的数据，可能为 None（比如出错了就没数据）
    data: Any = None

    # 这是一个「类方法」：用 Response.success(...) 就能快速造一个成功的响应
    # cls 指这个类本身，等价于 Response(...)
    @classmethod
    def success(cls, message: str = "请求成功", data: Any = None):
        return cls(code=200, message=message, data=data)

    # 同理，造一个失败的响应；默认 code=500，可按需传别的错误码
    @classmethod
    def error(cls, code: int = 500, message: str = "请求失败"):
        return cls(code=code, message=message)
