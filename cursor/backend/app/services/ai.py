# AI 助手业务层（service）：负责「拼提示词 → 调大模型 → 取回答」
# 按分层规范：业务错误只抛 BusinessException；大模型客户端的创建与调用都在这里，
# api 层只传参数、拿结果。
#
# 能力：
#   1. RAG：从 knowledge/ 知识库检索相关问答拼进上下文（静态规则类问题直接查知识库）
#   2. Tool Calling：自动调用工具——查询实验室 / 设备 / 我的预约（只读），
#      以及提交预约 / 取消预约（写操作，必须先经用户确认）

# json：解析模型传的工具参数、序列化工具结果
import json

# datetime：把「当前时间」注入系统提示词，让模型能把「明天/后天/周几」换算成具体日期
from datetime import datetime

# OpenAI 官方 SDK：DeepSeek 兼容 OpenAI 接口规范，直接用它的客户端即可
from openai import OpenAI

# 业务异常：统一错误出口，全局处理器会包成 {code, message, data} 返回
from common.exceptions import BusinessException

# 配置：LM_API_KEY / LM_BASE_URL / LM_MODEL 都从 .env 读进来
from app.config import settings

# 请求模型：给 chat() 做类型标注
from app.schemas.ai import ChatRequest

# RAG 知识库服务：检索 knowledge/ 里的答疑知识库，把相关内容拼进上下文
from app.services import kb_service

# 工具定义与分发：大模型可调用的 6 个工具（4 个查询 + 提交/取消预约 2 个写工具）
from app.services import ai_tools

# 工具调用最大轮数：预约流程可能是「查实验室 → 查设备 → 汇总确认 → 提交」多步操作，
# 超过这个上限说明对话跑偏了，兜底结束，防止接口挂死
MAX_TOOL_ROUNDS = 6


# 系统提示词：决定 AI 的「人设」和回答边界，每次对话都放在 messages 最前面
# 注意：chat() 里还会在末尾动态追加「当前时间」，让模型能把「明天/后天/周几」换算成具体日期
SYSTEM_PROMPT = (
    # 角色设定
    "你是「智能实验室预约系统」的 AI 预约助手，请用简体中文回答，内容简洁（一般不超过 200 字）。\n"
    "\n"
    # 你能做什么
    "你可以：\n"
    "1. 回答预约规则、功能入口等使用问题；\n"
    "2. 调用工具帮当前登录用户查询真实数据（实验室 / 设备 / 我的预约）；\n"
    "3. 帮当前登录用户提交预约、取消预约。\n"
    "\n"
    # 提交 / 取消预约的铁律（防乱来）
    "提交 / 取消预约的规则（必须严格遵守）：\n"
    "1. 提交预约前，必须先把信息汇总给用户确认（实验室名称和 id、日期、开始时间、结束时间、用途、设备），"
    "汇总时要写出换算好的具体日期（YYYY-MM-DD）和时间（HH:MM）；"
    "只有用户明确回复「确认 / 可以 / 提交」后，才允许调用 create_reservation。\n"
    "2. 用户确认后，必须按汇总里的实验室 id 调用 create_reservation，不得擅自更换实验室或时间；"
    "若工具返回的实验室名称与用户要求不一致，立即如实告知用户并停止提交。\n"
    "3. 用户信息不全时，先追问缺失项（实验室、日期、开始时间、结束时间、用途必填；设备可选），"
    "不要自己编造实验室、日期或时间。\n"
    "4. 时间必须换算成 YYYY-MM-DD 和 HH:MM（24 小时制）再传给工具。\n"
    "5. 只能为当前登录用户本人预约 / 取消，不能代他人操作。\n"
    "6. 工具返回错误（如时段冲突、实验室停用）时，如实把原因告诉用户，并给出替代建议（换时间 / 换实验室）。\n"
    "7. 只有 create_reservation 返回成功，才能告诉用户「已提交」；绝不编造预约成功。\n"
    "\n"
    # 查询类工具规则
    "查询工具使用规则：\n"
    "1. 用户问「有哪些实验室 / 某实验室详情 / 某实验室有哪些设备 / 我的预约」时，"
    "必须调用对应的查询工具，用返回的真实数据回答，不要凭记忆或知识库猜测。\n"
    "2. 取消预约时，先调 list_my_reservations 找到目标预约的 id，然后直接调用 cancel_reservation 取消"
    "（取消不需要再次确认），并把结果如实告诉用户。\n"
    "\n"
    # 你不能做什么（防编造）
    "限制：\n"
    "1. 工具没返回的数据（如某实验室的开放时间、是否空闲）不要编造，"
    "如实说明并引导用户去「实验室列表」页面查看。\n"
    "2. 与本系统使用无关的话题，礼貌说明你只负责本系统的使用咨询，并把话题拉回预约 / 功能使用。"
)


# 创建大模型客户端：把「读配置 → 建 OpenAI 客户端」收口到一个函数里
def get_client() -> OpenAI:
    """用 .env 里的 LM_API_KEY / LM_BASE_URL 创建 OpenAI 兼容客户端

    密钥缺失时直接抛业务异常，接口会返回「AI 服务未配置」，而不是让调用堆栈报 500。
    """
    # 密钥为空（或全是空格）视为未配置
    if not settings.LM_API_KEY or not settings.LM_API_KEY.strip():
        raise BusinessException("AI 服务未配置", code=400)
    # DeepSeek 兼容 OpenAI 接口：指定 base_url 即可指向 DeepSeek 服务
    # timeout=30：网络卡住最多等 30 秒，避免接口长时间挂起
    return OpenAI(
        api_key=settings.LM_API_KEY,
        base_url=settings.LM_BASE_URL,
        timeout=30.0,
    )


# 调用大模型一轮（带工具定义）：异常统一包成 BusinessException
def _call_model(client: OpenAI, messages: list[dict]):
    """发起一次带 tools 的对话补全，任何异常统一转业务错误"""
    try:
        return client.chat.completions.create(
            model=settings.LM_MODEL,
            messages=messages,
            tools=ai_tools.TOOLS,   # 告诉模型它有哪些工具可用
            tool_choice="auto",     # 模型自己决定：直接用知识回答，还是先调工具
        )
    except Exception:
        # 注意：这里故意不把原始异常信息透出去（可能含密钥 / 内部地址）
        raise BusinessException("大模型调用失败，请稍后重试", code=400)


# 执行单个工具调用：参数解析 + 分发 + 序列化，任何错误都转成 {"error": ...} 文本
def _run_tool(tool_call, db, current_user) -> str:
    """执行模型请求的单个工具调用，返回 JSON 字符串结果

    工具参数缺失 / 业务报错 / 意外异常，全部转成 {"error": "..."} 回填给模型，
    让模型向用户解释原因——绝不向上抛异常（保证接口不会 500）。
    """
    # 1. 解析模型传来的参数 JSON；解析失败按空参数处理（dispatch 会做必填校验）
    try:
        args = json.loads(tool_call.function.arguments or "{}")
    except Exception:
        args = {}
    if not isinstance(args, dict):
        args = {}

    # 2. 白名单分发执行工具
    try:
        result = ai_tools.dispatch(tool_call.function.name, args, db, current_user)
    except BusinessException as exc:
        # 业务错误（如「实验室不存在」「缺少必填参数」）→ 把错误信息给模型解释
        return json.dumps({"error": exc.message}, ensure_ascii=False)
    except Exception as exc:
        # 其它意外错误同样回填，绝不 500
        return json.dumps({"error": f"工具执行失败：{exc}"}, ensure_ascii=False)

    # 3. 结果序列化：ensure_ascii=False 保留中文；default=str 兜底 date/time 等类型
    return json.dumps(result, ensure_ascii=False, default=str)


# 对话主流程：校验 → 拼消息（含 RAG）→ 工具调用循环 → 取回答
def chat(db, current_user, data: ChatRequest) -> str:
    """处理一轮对话：RAG 拼上下文 + 工具调用循环，返回大模型的回答文本

    参数：
      db           —— 数据库会话（工具查真实数据用）
      current_user —— 当前登录用户（工具只允许查这个人自己的预约）
      data         —— 本轮请求 {message, history}
    空消息、模型没返回内容、网络 / 密钥异常仍抛 BusinessException（保持原约定）。
    """
    # 1. 校验用户输入：去掉首尾空格后不能为空
    if not data.message or not data.message.strip():
        raise BusinessException("请输入您要对话的内容", code=400)

    # 2. 创建客户端（密钥未配置会在这里抛「AI 服务未配置」）
    client = get_client()

    # 3. 组装 messages：系统提示词（含当前时间）+（RAG 知识库上下文）+ 历史对话 + 本轮提问
    #    把当前时间注入系统提示词：模型才知道「今天」是哪天，能把「明天/后天/周几」换算成具体日期
    now = datetime.now()
    weekday = "一二三四五六日"[now.weekday()]  # weekday()：周一=0，取汉字拼成「周一」样式
    time_hint = (
        f"\n当前时间是 {now:%Y-%m-%d %H:%M}（周{weekday}）。"
        "用户说「明天」「后天」「周几」时，请据此换算成具体日期，日期用 YYYY-MM-DD、时间用 HH:MM。"
    )
    messages = [{"role": "system", "content": SYSTEM_PROMPT + time_hint}]

    # RAG：从知识库检索与本轮问题最相关的问答，作为附加上下文，让助手按知识库精准回答。
    # build_context 内部已兜底（检索失败 / 无结果时返回空串），不会影响主流程
    kb_context = kb_service.build_context(data.message, top_k=settings.KB_TOP_K)
    if kb_context:
        messages.append({"role": "system", "content": kb_context})

    # 历史消息按原顺序插入（schema 已校验过 role 只能是 system/user/assistant）
    for m in data.history or []:
        messages.append({"role": m.role, "content": m.content})
    # 最后放本轮用户输入（去掉首尾空格，避免把无意义的空白发给模型）
    messages.append({"role": "user", "content": data.message.strip()})

    # 4. 工具调用主循环：模型可能「调工具 → 看结果 → 再调工具 → …」连续多轮，
    #    例如预约要「查实验室 → 汇总确认 → 提交」，所以用 for 循环而不是一次就返回；
    #    最多转 MAX_TOOL_ROUNDS 轮，防止模型反复调工具把接口拖死
    for _ in range(MAX_TOOL_ROUNDS):
        # 4.1 调一次模型：带上 tools 定义，模型自己决定这轮是直接回答还是先调工具
        resp = _call_model(client, messages)
        # 取模型这轮的回复（message 里可能带 content 文本，也可能带 tool_calls 调用清单）
        message = resp.choices[0].message

        # 4.2 模型没要求调工具（tool_calls 为空）→ content 就是最终回答，直接返回
        if not getattr(message, "tool_calls", None):
            reply = message.content
            # 回答为空（None / 空串）同样按业务错误处理
            if not reply or not str(reply).strip():
                raise BusinessException("大模型没有返回内容", code=400)
            return str(reply).strip()

        # 4.3 模型要求调工具：必须先把「带 tool_calls 的 assistant 消息」原样放回 messages，
        #     这是 OpenAI 工具调用协议的硬性要求——模型下一轮要靠它
        #     把自己的调用请求和回填结果一一对上号
        messages.append(
            {
                "role": "assistant",              # 这条是模型（助手）发的
                "content": message.content or "", # 正文可能为空（只调工具不说话的情况）
                "tool_calls": [                   # 模型想调用的工具清单
                    {
                        "id": tc.id,              # 每次调用有唯一 id（回填结果时必须对应）
                        "type": "function",       # 固定写法：函数类调用
                        "function": {             # 调哪个函数、传什么参数
                            "name": tc.function.name,          # 工具名（dispatch 按它路由）
                            "arguments": tc.function.arguments,  # 参数 JSON 字符串
                        },
                    }
                    for tc in message.tool_calls  # 一轮可能同时调多个工具，逐个搬进来
                ],
            }
        )

        # 4.4 逐个执行工具：每条结果都以 tool 消息回填
        for tc in message.tool_calls:
            # 执行工具：解析参数 → dispatch 查库/写库 → 序列化结果
            # （工具出错也会返回 {"error": ...} 文本，绝不会中断对话）
            result_text = _run_tool(tc, db, current_user)
            # role 必须是 "tool"、tool_call_id 必须与 4.3 里的 id 一一对应，
            # 错位会导致模型把工具结果张冠李戴
            messages.append(
                {"role": "tool", "tool_call_id": tc.id, "content": result_text}
            )
        # 本轮结束 → 回到循环开头：模型下一轮会看到工具结果，再决定继续调工具还是最终回答

    # 5. 超过最大轮数模型还没结束（一直来回调工具）→ 兜底回答，防止接口挂死
    return "这个问题需要多步操作，请分步告诉我"
