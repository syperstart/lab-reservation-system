# 演示数据初始化：仅当 lab / device 表为空时插入，重复启动不会重复写入
# 在 app/main.py 的 lifespan 里调用（服务首次启动、且库里没数据时自动填充）

# 数据库会话工厂：每次拿到一个独立会话
from app.database import SessionLocal

# 模型：实验室 + 设备
from app.model.lab import Lab
from app.model.device import Device


def seed_data():
    """写入演示数据：4 个实验室 + 8 台设备；表非空则跳过，保证幂等。"""
    # 自己开一个会话，用完即关，不依赖接口层的 Depends(get_db)
    db = SessionLocal()
    try:
        # —— 1. 实验室：表为空才插入 ——
        if db.query(Lab).count() == 0:
            labs = [
                Lab(name="软件工程实验室", code="SOFT-301", location="实验楼A-301", capacity=60, status=1),
                Lab(name="机器人实验室", code="ROBOT-205", location="实验楼B-205", capacity=40, status=1),
                Lab(name="人工智能实验室", code="AI-402", location="实验楼A-402", capacity=45, status=1),
                Lab(name="网络工程实验室", code="NET-101", location="实验楼C-101", capacity=50, status=1),
            ]
            db.add_all(labs)
            db.commit()
            # 让 lab.id 回填，方便下面设备关联
            for l in labs:
                db.refresh(l)

        # —— 2. 设备：表为空才插入 ——
        if db.query(Device).count() == 0:
            # 用实验室名称反查 id（与截图数据对应）
            lab_map = {l.name: l.id for l in db.query(Lab).all()}

            # 软件工程实验室 4 台
            soft = lab_map["软件工程实验室"]
            # 机器人实验室 4 台
            robot = lab_map["机器人实验室"]

            devices = [
                Device(lab_id=soft, name="代码服务器", model="8核 / 32G", quantity=1, status=1, description="Git 与 CI"),
                Device(lab_id=soft, name="控制仪", model="1080P", quantity=2, status=1, description=""),
                Device(lab_id=soft, name="显示器", model="27寸 2K", quantity=40, status=1, description=""),
                Device(lab_id=soft, name="开发主机", model="i7 / 32G / 1T SSD", quantity=40, status=1, description=""),
                Device(lab_id=robot, name="Jetson Orin", model="32G", quantity=4, status=1, description=""),
                Device(lab_id=robot, name="RealSense 深度相机", model="D435i", quantity=4, status=1, description=""),
                Device(lab_id=robot, name="Livex 激光雷达", model="Mid-360", quantity=3, status=1, description=""),
                Device(lab_id=robot, name="UR5 机械臂", model="负载 5kg", quantity=2, status=1, description=""),
            ]
            db.add_all(devices)
            db.commit()
    finally:
        # 无论成功失败都关闭会话，把连接还回连接池
        db.close()
