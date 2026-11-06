# 智能实验室预约系统

高校实验室预约管理系统：学生可在线查看实验室与设备并提交预约，管理员维护实验室/设备数据、审核预约、管理账号，内置 AI 智能助手（RAG 知识库 + 工具调用）。

## 技术栈

| 端 | 技术 |
|---|---|
| 前端 | Vue 3 + TypeScript + Vite + Element Plus + Vue Router + Axios |
| 后端 | Python 3.12 + FastAPI + SQLAlchemy + MySQL + PyJWT |
| AI | DeepSeek（OpenAI 兼容）+ ChromaDB 向量检索（RAG）+ Function Calling |
| 部署 | Nginx 反向代理 + systemd 守护 |

## 目录结构

```
├── cursor/
│   ├── backend/            # FastAPI 后端
│   │   ├── app/
│   │   │   ├── api/        # 接口层（路由）
│   │   │   ├── services/   # 业务逻辑层（含 AI / RAG / 工具调用）
│   │   │   ├── model/      # 数据模型（user/lab/device/appointment）
│   │   │   ├── schemas/    # 请求/响应模型
│   │   │   ├── dependencies/  # 登录鉴权、权限
│   │   │   └── utils/      # JWT、密码、文件上传等工具
│   │   ├── knowledge/      # AI 助手答疑知识库（Markdown Q&A）
│   │   ├── common/         # 统一响应信封 + 全局异常
│   │   ├── main.py         # 兼容入口
│   │   └── requirements.txt
│   └── frontend/           # Vue3 前端
│       └── src/
│           ├── views/      # 页面
│           ├── router/     # 路由与守卫
│           ├── stores/     # 全局状态
│           ├── layouts/    # 布局
│           └── utils/      # axios 封装
├── DEPLOY.md               # 腾讯云部署手册
└── .gitignore
```

## 功能

- 登录 / 注册（JWT，角色：管理员 / 学生）
- 学生端：实验室列表、设备查看、提交预约、我的预约（取消）、个人信息、AI 智能助手
- 管理端：实验室管理、设备管理、预约审核、账号管理
- AI 智能助手：RAG 知识库问答 + 工具调用（查实验室/设备/我的预约、提交/取消预约）
- 文件上传（头像、设备图片）

## 本地运行

### 后端

```bash
cd cursor/backend
python -m venv .venv
source .venv/bin/activate        # Windows: .\.venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # 配置数据库 / DeepSeek Key
.venv/bin/uvicorn app.main:app --reload   # Windows: .\.venv\Scripts\uvicorn.exe
```

### 前端

```bash
cd cursor/frontend
npm install
npm run dev
```

前端开发服务器默认 `http://localhost:5173`，通过 Vite 代理访问后端 `8000`。

## 部署

见 [DEPLOY.md](./DEPLOY.md)，采用 Nginx 反代 + systemd 守护，支持腾讯云轻量应用服务器 / CVM。
