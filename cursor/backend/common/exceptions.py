# 自定义异常 + 全局异常处理器
# 作用：业务代码里只要写 raise BusinessException("出错了", code=400)，
#       就会被这里统一捕获，自动返回一个标准格式的 Response.error(...)，
#       前端不用在每个接口里单独写错误返回。

# HTTPException 是 FastAPI 自带的异常（比如 401/404 用它抛出）
# Request 是请求对象：异常处理器函数必须接收它（即便函数体里没用到）
from fastapi import HTTPException, Request

# 请求参数校验失败（比如前端字段类型不对）时，FastAPI 会抛这个异常
# 注：教程后面通常会再写一个「校验异常处理器」来用它，这里先导入备用
from fastapi.exceptions import RequestValidationError

# JSONResponse 用来手动拼一个 JSON 响应返回给前端
from fastapi.responses import JSONResponse

# 导入我们刚写的统一响应格式工具
# 注意：本项目的 common 在 backend 根目录下，所以导入路径是 common.response
#       （不是视频里的 app.common.response，那是视频把 common 放在 app 包里的写法）
from common.response import Response


class BusinessException(Exception):
    """自定义的业务异常（业务层主动抛出的错误，比如「用户名已存在」）"""

    def __init__(self, message: str, code: int = 500):
        self.message = message
        self.code = code
        # 调用父类 Exception 的初始化，把 message 作为位置参数传进去
        # 注意：Exception.__init__ 只接受位置参数，不能写 message= 这种关键字形式
        super().__init__(message)


# 这是一个「异常处理器」：FastAPI 捕获到 BusinessException 时会自动调用它
# 函数名 handler 是「处理器」的意思（视频里拼成了 hadler，这里纠正为正确拼写）
async def business_exception_handler(request: Request, exc: Exception):
    """自定义业务异常处理器"""
    # 注册时只绑定 BusinessException，这里断言一下类型，方便下面取 .code / .message
    assert isinstance(exc, BusinessException)
    return JSONResponse(
        # 一律返回 HTTP 200，真正的成败由业务 code 字段告诉前端
        status_code=200,
        content=Response.error(code=exc.code, message=exc.message).model_dump(),
    )


# ---------------------------------------------------------------------------
# 下面三个是 FastAPI 自带异常的「统一格式」处理器，配合上面的 BusinessException 一起用
# ---------------------------------------------------------------------------

# 处理 FastAPI 自带的 HTTPException（比如接口里 raise HTTPException(status_code=401, detail="xxx")）
async def http_exception_handler(request: Request, exc: Exception):
    """HTTP 异常处理器：把 401/404 等也包成统一格式返回"""
    # 注册时只绑定 HTTPException，断言类型后取 status_code / detail
    assert isinstance(exc, HTTPException)
    return JSONResponse(
        # 这里用真实的 HTTP 状态码（如 401），让前端既能看 code 也能看 HTTP 状态
        status_code=exc.status_code,
        content=Response.error(code=exc.status_code, message=exc.detail).model_dump(),
    )


# 处理「请求参数校验失败」（比如前端传的字段类型不对、少了必填项）
async def validation_exception_handler(request: Request, exc: Exception):
    """参数校验异常处理器"""
    # 注册时只绑定 RequestValidationError，断言类型（这里没用到 exc 的具体字段）
    assert isinstance(exc, RequestValidationError)
    return JSONResponse(
        status_code=422,
        content=Response.error(code=422, message="请求参数校验失败").model_dump(),
    )


# 全局兜底：任何没被上面捕获的异常（比如代码写错导致的 500）都会到这里
# 注意：全局处理器必须【最后】注册，否则会盖掉更具体的处理器
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理器（兜底）"""
    return JSONResponse(
        status_code=500,
        content=Response.error(code=500, message="服务器内部错误，请联系管理员").model_dump(),
    )
