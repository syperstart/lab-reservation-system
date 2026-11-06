# AI 助手的「工具」层：定义大模型可调用的函数（OpenAI Function Calling 格式）+ 统一分发执行
#
# 本文件分两部分：
#   第一部分 TOOLS      —— 工具定义：告诉大模型「有哪些工具、每个工具要什么参数」
#   第二部分 dispatch() —— 工具执行：模型点名要调哪个工具时，真正去查库 / 写库
#
# 安全原则（必须遵守）：
#   1. 用户身份只信 current_user（登录态），工具参数里绝不允许出现 user_id——
#      模型想传什么参数都行，但「我的预约 / 提交 / 取消」一律只作用于当前登录用户本人
#   2. 白名单路由：只有 TOOLS 里定义过的工具名才会被执行，未知名字直接拒绝
#   3. 工具报错统一抛 BusinessException，由 ai.py 回填成 {"error": ...} 给模型解释，不 500

# Session / User：给分发函数做类型标注
from sqlalchemy.orm import Session
from app.model.user import User

# datetime：把模型传来的 "YYYY-MM-DD" / "HH:MM" 字符串转成 date / time 对象
from datetime import datetime

# 复用已有 service（查询 / 预约 / 取消的业务逻辑都不在这里重写）
from app.services import appointment_service
from app.services import lab_service

# 业务异常：参数缺失、格式错误、未知工具名等错误统一用它抛
from common.exceptions import BusinessException

# =====================================================================
# 第一部分：TOOLS 工具定义（OpenAI Function Calling 标准格式）
# =====================================================================
# 作用：这段 JSON 会原样发给大模型，模型看完就知道「什么时候该调哪个工具、参数怎么填」。
#
# 每条定义的字段含义（以工具 1 为例，后面工具结构完全一样）：
#   "type": "function"        —— 固定写法：这是一个「函数类」工具
#   "function.name"           —— 工具唯一名字；模型调用时用这个名字，
#                               必须与下面 dispatch 的白名单 if/elif 完全一致
#   "function.description"    —— 给模型看的用途说明：写得越清楚，模型越不会乱调 / 乱填参数
#   "function.parameters"     —— 参数说明（JSON Schema）：
#       "type": "object"      ——   参数整体是一个 JSON 对象
#       "properties"          ——   逐个声明参数：每个参数有 type（类型）、description（说明）、
#                                  enum（可选，限定取值范围）
#       "required"            ——   必填参数名单：模型少传时 dispatch 会报「缺少必填参数」
#   "additionalProperties": False —— 模型只能传声明过的参数，不允许乱加字段
# =====================================================================
TOOLS = [
    # ---------- 工具 1：实验室列表（只读查询） ----------
    {
        "type": "function",  # 固定写法：函数类工具
        "function": {
            "name": "list_labs",  # 工具名（dispatch 里必须有一模一样的分支）
            "description": "查询可预约的实验室列表（可传关键字按名称筛选）",  # 给模型看的用途
            "parameters": {
                "type": "object",  # 参数整体是一个对象
                "properties": {
                    "keyword": {  # 参数一：关键字（选填）
                        "type": "string",  # 类型：字符串
                        "description": "按实验室名称筛选的关键字，可选",
                    }
                },
                # 本工具没有必填参数，所以不写 required 字段
                "additionalProperties": False,  # 不许模型乱传没声明的参数
            },
        },
    },

    # ---------- 工具 2：实验室详情（只读查询） ----------
    {
        "type": "function",
        "function": {
            "name": "get_lab_detail",
            "description": "查询某个实验室的详细信息（位置、容量、开放时间）",
            "parameters": {
                "type": "object",
                "properties": {
                    "lab_id": {"type": "integer", "description": "实验室 id，必填"}  # 必填参数
                },
                "required": ["lab_id"],  # 声明必填：模型少传时 dispatch 会报「缺少必填参数」
                "additionalProperties": False,
            },
        },
    },

    # ---------- 工具 3：某实验室的设备列表（只读查询） ----------
    {
        "type": "function",
        "function": {
            "name": "list_lab_devices",
            "description": "查询某个实验室下的设备列表",
            "parameters": {
                "type": "object",
                "properties": {
                    "lab_id": {"type": "integer", "description": "实验室 id，必填"},
                    "status": {  # 选填：只查某种状态的设备
                        "type": "integer",
                        "enum": [0, 1],  # 限定取值：模型只能传 0 或 1
                        "description": "设备状态筛选：1=正常，0=维修；不传表示全部",
                    },
                },
                "required": ["lab_id"],
                "additionalProperties": False,
            },
        },
    },

    # ---------- 工具 4：我的预约（只读查询，只查本人） ----------
    {
        "type": "function",
        "function": {
            "name": "list_my_reservations",
            "description": "查询当前登录用户自己的预约记录，可按状态筛选",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {  # 选填：按预约状态筛选
                        "type": "integer",
                        "enum": [0, 1, 2, 3, 4],  # 限定五种状态取值
                        "description": "预约状态筛选：0=待审核 1=已通过 2=已拒绝 3=已取消 4=已结束；不传表示全部",
                    }
                },
                # 注意：这里故意不提供 user_id 参数——身份由服务端登录态决定，
                # 从参数层面杜绝「查别人预约」的可能
                "additionalProperties": False,
            },
        },
    },

    # ---------- 工具 5：提交预约（写工具） ----------
    {
        "type": "function",
        "function": {
            "name": "create_reservation",
            "description": "为当前登录学生提交一条实验室预约（必须先与用户确认信息后才能调用）",
            "parameters": {
                "type": "object",
                "properties": {
                    "lab_id": {"type": "integer", "description": "实验室 id，必填"},
                    "appoint_date": {"type": "string", "description": "预约日期，格式 YYYY-MM-DD，必填"},  # 字符串，dispatch 里转 date
                    "start_time": {"type": "string", "description": "开始时间，格式 HH:MM（24 小时制），必填"},  # 字符串，dispatch 里转 time
                    "end_time": {"type": "string", "description": "结束时间，格式 HH:MM（24 小时制），必填"},
                    "purpose": {"type": "string", "description": "预约用途，必填"},
                    "device_id": {"type": "integer", "description": "设备 id，可选；不指定设备就不传"},  # 选填
                },
                "required": ["lab_id", "appoint_date", "start_time", "end_time", "purpose"],  # 五个必填
                "additionalProperties": False,
            },
        },
    },

    # ---------- 工具 6：取消预约（写工具，只能取消本人） ----------
    {
        "type": "function",
        "function": {
            "name": "cancel_reservation",
            "description": "取消当前登录学生自己的某条预约",
            "parameters": {
                "type": "object",
                "properties": {
                    "reservation_id": {"type": "integer", "description": "要取消的预约记录 id，必填"}
                },
                "required": ["reservation_id"],
                "additionalProperties": False,
            },
        },
    },
]


# =====================================================================
# 第二部分：dispatch 工具分发（白名单 if/elif）
# =====================================================================
def dispatch(name: str, args: dict, db: Session, current_user: User):
    """执行一个工具：按名字路由到对应 service，返回可 JSON 序列化的 dict / list

    约定：
    - 白名单路由：不在白名单里的工具名 → BusinessException("不支持的工具")
    - 必填参数缺失 / 格式错误 → BusinessException（由 ai.py 回填给模型，不 500）
    - user_id 一律取 current_user.id，绝不接受模型传来的 user_id
    """
    # ---- 工具 1：实验室列表（keyword 可选，缺了也无所谓） ----
    if name == "list_labs":
        # args.get 而不是 args[...]：取不到就返回 None，交给 service 处理
        return lab_service.list_labs(db, keyword=args.get("keyword"))

    # ---- 工具 2：实验室详情（lab_id 必填） ----
    if name == "get_lab_detail":
        lab_id = args.get("lab_id")  # 取出模型给的 lab_id
        if lab_id is None:           # 必填校验：没传就明确报错（会回填给模型）
            raise BusinessException("缺少必填参数 lab_id", code=400)
        return lab_service.get_lab(db, lab_id=lab_id)

    # ---- 工具 3：某实验室的设备（lab_id 必填，status 可选） ----
    if name == "list_lab_devices":
        lab_id = args.get("lab_id")
        if lab_id is None:
            raise BusinessException("缺少必填参数 lab_id", code=400)
        # status 不传就是 None → service 里查全部设备
        return lab_service.list_lab_devices(
            db, lab_id=lab_id, status=args.get("status")
        )

    # ---- 工具 4：我的预约（status 可选；只能查当前登录用户自己） ----
    if name == "list_my_reservations":
        rows, total = appointment_service.list_my_reservations(
            db,
            user_id=current_user.id,  # 安全关键：身份只来自登录态，绝不接受模型传的 user_id
            page=1,                   # 固定第一页
            page_size=50,             # 最多 50 条：足够回答，又防止结果过长撑爆上下文
            status=args.get("status"),  # 选填：None=查全部
        )
        # 返回总数 + 列表：模型既能回答「有几条」，也能逐条描述
        return {"total": total, "list": rows}

    # ---- 工具 5：提交预约（写工具；只能给当前登录用户本人预约） ----
    if name == "create_reservation":
        # 先把模型传来的参数全部取出（模型传的几乎都是字符串，下面逐个转类型）
        lab_id = args.get("lab_id")             # 实验室 id（可能是字符串 → 下面转 int）
        appoint_date = args.get("appoint_date") # 预约日期字符串，格式要求 "YYYY-MM-DD"
        start_time = args.get("start_time")     # 开始时间字符串，格式要求 "HH:MM"
        end_time = args.get("end_time")         # 结束时间字符串，格式要求 "HH:MM"
        purpose = args.get("purpose")           # 用途
        device_id = args.get("device_id")       # 设备 id（可选）

        # 必填校验：缺任何一个都提示清楚，不让 service 收到残缺参数
        if (
            not lab_id
            or not appoint_date
            or not start_time
            or not end_time
            or not str(purpose).strip()  # 用途还要排除「纯空格」这种情况
        ):
            raise BusinessException(
                "缺少必填参数：lab_id / appoint_date / start_time / end_time / purpose",
                code=400,
            )

        # 类型转换 1：lab_id 可能是字符串（模型偶尔传 "2" 而不是 2）→ 转整数
        try:
            lab_id = int(lab_id)
        except (TypeError, ValueError):
            raise BusinessException("参数格式不正确：lab_id 必须是整数", code=400)

        # 类型转换 2：模型给的是字符串，service 要的是 date / time 对象
        # "YYYY-MM-DD" → datetime.date；"HH:MM" → datetime.time
        # （过去时间、开始早于结束等业务校验在 appointment_service 里，这里只负责转类型）
        try:
            d = datetime.strptime(str(appoint_date).strip(), "%Y-%m-%d").date()
            st = datetime.strptime(str(start_time).strip(), "%H:%M").time()
            et = datetime.strptime(str(end_time).strip(), "%H:%M").time()
        except ValueError:
            # 格式对不上（如「明天」「9点」这种没换算的）→ 统一报格式错误，回填给模型
            raise BusinessException("参数格式不正确，需要 YYYY-MM-DD 和 HH:MM", code=400)

        # 类型转换 3：device_id 可选——没传或空串都按「不指定设备」处理
        try:
            device_id = int(device_id) if device_id not in (None, "") else None
        except (TypeError, ValueError):
            raise BusinessException("参数格式不正确：device_id 必须是整数", code=400)

        # 真正提交：user_id 强制取当前登录用户（安全：只能给自己预约）
        # 过去时间 / 时间顺序 / 实验室启用 / 设备归属 / 时段冲突 的校验都在 service 里，
        # 校验不过会抛 BusinessException，ai.py 会把原因回填给模型解释
        return appointment_service.create_reservation(
            db,
            user_id=current_user.id,
            lab_id=lab_id,
            device_id=device_id,
            appoint_date=d,
            start_time=st,
            end_time=et,
            purpose=str(purpose).strip(),
        )

    # ---- 工具 6：取消预约（写工具；只能取消自己的预约） ----
    if name == "cancel_reservation":
        reservation_id = args.get("reservation_id")
        if reservation_id is None:
            raise BusinessException("缺少必填参数 reservation_id", code=400)
        try:
            reservation_id = int(reservation_id)  # 字符串 → 整数
        except (TypeError, ValueError):
            raise BusinessException("参数格式不正确：reservation_id 必须是整数", code=400)
        # 取消：service 内部校验「仅本人 + 仅待审核/已通过可取消」，校验不过会抛异常
        return appointment_service.cancel_reservation(
            db, reservation_id=reservation_id, user_id=current_user.id
        )

    # ---- 白名单之外的工具名 → 明确拒绝（防止模型幻觉出奇怪的调用） ----
    raise BusinessException("不支持的工具", code=400)
