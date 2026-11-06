"""智能预约系统 · 兼容入口（薄包装层，不建议再往这里写业务代码）

真正的应用在 app/main.py。这个文件只为兼容老命令而保留：
    uvicorn main:app --reload      # 老命令，仍然可用
    uvicorn app.main:app --reload  # 推荐命令
"""

# 直接把 app/main.py 里创建好的 FastAPI 对象拿过来，两条命令拿到的是同一个应用
from app.main import app

# 只有直接运行 python main.py 时才会走这里；用 uvicorn 命令启动时不会执行
if __name__ == "__main__":
    # 在函数内部导入，避免用命令行启动时多余加载
    import uvicorn

    # 用包名路径启动，保证 --reload 重新加载的也是 app/main.py
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
