# AI 助手相关的请求 / 响应数据模型
# Pydantic 会自动校验前端传来的 JSON 结构，不合法直接 422（全局处理器统一格式）

# Literal：限定只能取某几个字符串字面量（这里限定角色只能是 system/user/assistant）
from typing import Literal

# BaseModel = 数据模型父类；Field = 给字段加校验 / 描述
from pydantic import BaseModel, Field


# 单条对话消息：历史记录里的每一条
class ChatMessage(BaseModel):
    # 角色：只能 system（系统设定）/ user（用户）/ assistant（AI 回复）三选一
    role: Literal["system", "user", "assistant"]

    # 消息内容：必填，不允许空字符串
    content: str = Field(min_length=1, description="消息内容")


# 发起对话的请求体：POST /api/ai/chat 的 body
class ChatRequest(BaseModel):
    # 本轮用户提问：必填（service 层还会再校验一次纯空格的情况）
    message: str = Field(description="用户本次输入的内容")

    # 历史对话：可选（首轮为空列表）；带上它模型才能理解上下文
    history: list[ChatMessage] = Field(default=[], description="之前的对话历史")


# 对话响应的数据部分：data 里就一个 reply 字段
class ChatResponse(BaseModel):
    # 大模型生成的回答文本
    reply: str
