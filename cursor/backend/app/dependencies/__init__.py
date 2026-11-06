# 依赖包标记文件：把 dependencies 变成一个可以被 import 的 Python 包
# 这个目录专门放「各个接口复用的公共依赖」，目前有 auth.py（校验当前登录用户）
# 以后业务接口里写 Depends(get_current_user)，就能自动完成登录校验
