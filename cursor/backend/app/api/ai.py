# AI 助手接口：只做「接收请求 → 调 service → 统一返回」
# 完整路径：POST /api/ai/chat（/api 来自总路由，/ai 是本文件前缀）
# 业务逻辑（提示词、客户端创建、异常包装、工具调用）全部在 app/services/ai.py

from fastapi import APIRouter, Depends

# 数据库会话依赖：工具调用要查实验室 / 设备 / 预约的真实数据
from sqlalchemy.orm import Session
from app.database import get_db

# 登录校验依赖：AI 助手必须登录后才能用（不带 token 直接 401）
from app.dependencies.auth import get_current_user

# 用户模型：给依赖注入的返回值做类型标注
from app.model.user import User

# 请求 / 响应模型
from app.schemas.ai import ChatRequest, ChatResponse

# AI 业务层
from app.services import ai_service

# 统一响应信封
from common.response import Response

# 子路由前缀 /ai（总路由再统一加 /api）
router = APIRouter(prefix="/ai", tags=["AI助手"])


# 对话接口：带上历史记录即可多轮对话；助手可按需调用只读工具查真实数据
@router.post("/chat")
def chat(
    # 请求体：{ message: "用户输入", history: [{role, content}, ...] }
    data: ChatRequest,
    # 数据库会话：给工具调用查真实数据用
    db: Session = Depends(get_db),
    # 登录用户：工具只允许查这个用户自己的预约（身份只来自登录态）
    current_user: User = Depends(get_current_user),
):
    """与 AI 助手对话：返回大模型生成的回答（可自动调用只读工具查询真实数据）"""
    # 业务全在 service 里：空内容 / 未配置 / 调用失败都会以 BusinessException 抛出
    reply = ai_service.chat(db, current_user, data)
    # 用 ChatResponse 包一层，保证 data 的结构固定为 { reply: "..." }
    return Response.success(message="回答成功", data=ChatResponse(reply=reply))
