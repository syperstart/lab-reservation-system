# services 包：业务逻辑层（service layer）
#
# 分层规范（所有新代码必须遵守）：
#   1. 每个业务模块一个 *_service.py（如 appointment_service.py）
#   2. service 函数第一个参数固定是 db: Session（定时任务除外，自己用 SessionLocal 开会话）
#   3. 业务错误一律抛 BusinessException(message="...", code=400)，不抛 HTTPException
#   4. 数据库写入（add / commit / refresh）在 service 里完成
#   5. api 层只做：接收参数 → 调 service → return Response.success(...)
#   6. service 返回 ORM 对象或 dict/list，由 api 层转成 schema
#
# 渐进迁移策略：老接口保持原样能跑；本次只示范迁移了 appointment（预约）模块，
# 其余模块（auth/user/lab/device）等下次要改到时再顺手迁移。

# AI 助手模块：文件名叫 ai.py（按 spec 命名），但 api 层统一写 from app.services import ai_service。
# appointment_service 能直接导入，是因为它恰好有同名文件 appointment_service.py；
# ai 没有 ai_service.py，所以在这里显式起一个别名 ai_service，让 api 层一行导入就能用。
from app.services import ai as ai_service
