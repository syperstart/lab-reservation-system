# 异常处理器注册模块
# 把 common/exceptions.py 里写好的 4 个处理器，统一注册到 FastAPI 应用上。
# 这样业务代码里只要 raise 异常，就会被自动捕获并返回统一格式的响应。
#
# 对应教学视频里 main.py 的「注册自定义异常」那段代码，
# 我们把它单独抽成一个函数放在这里，入口 app/main.py 调用一次即可。

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError

# 导入我们写好的异常类与对应的处理器
from common.exceptions import (
    BusinessException,
    business_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    global_exception_handler,
)


def register_exception_handlers(app: FastAPI):
    """把自定义异常处理器注册到应用上（在 app/main.py 里调用一次即可）"""
    # 1. 自定义业务异常
    app.add_exception_handler(BusinessException, business_exception_handler)
    # 2. FastAPI 自带的 HTTP 异常（401/404 等）
    app.add_exception_handler(HTTPException, http_exception_handler)
    # 3. 请求参数校验失败
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    # 4. 全局兜底，必须放在最后注册！
    app.add_exception_handler(Exception, global_exception_handler)
