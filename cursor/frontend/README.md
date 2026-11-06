# 智能预约系统 · 前端

Vue 3 + TypeScript + Vite 8 + Element Plus 2.14。当前阶段为**登录页 + 后台导航骨架**，四个模块的业务内容已清空。

## 页面与路由

| 路径 | 页面 | 说明 |
| --- | --- | --- |
| `/login` | 登录页 | 独立全屏页面，标题「智能预约系统」，表单垂直水平居中 |
| `/` | — | 重定向到 `/login` |
| `/home` | 系统首页 | 空模块（仅占位提示） |
| `/laboratory` | 实验室管理 | 空模块 |
| `/device` | 设备列表管理 | 空模块 |
| `/user` | 用户管理 | 空模块 |

登录账号与密码均为 **admin**（已预填，登录成功后跳转 `/home`；右上角「退出登录」可返回登录页）。
四个模块共用 `views/EmptyModuleView.vue`，左侧导航与面包屑仍可正常切换。

## 目录结构

```
src/
├── main.ts                  # 入口：router + Element Plus（中文语言包）
├── App.vue                  # 仅 <router-view />
├── router/index.ts          # 路由表 + 页面标题
├── layouts/BasicLayout.vue  # 后台框架：顶部栏、四个侧边导航、面包屑、内容区
├── views/
│   ├── LoginView.vue        # 登录页（含分层背景、居中卡片、表单校验）
│   └── EmptyModuleView.vue  # 四个模块共用的空内容占位
└── assets/main.css          # 全局设计变量、Element Plus 主题覆盖、通用类
```

## 视觉规范

- 主色 `#2b6cf6`，页面底色 `#f5f7fb`；卡片白底 + 1px 边框 + 轻投影
- 登录页：渐变底 + 光晕/网格/圆环三层背景装饰，独立 `.bg-layer` 只裁剪装饰，不裁剪内容
- 登录卡片：悬浮 Logo 徽章、标题层级、46px 输入框、渐变登录按钮、演示账号提示条
- 自适应：小屏隐藏顶部辅助信息、缩小内边距；矮屏压缩间距；页面用 `min-height: 100vh` 且允许滚动，不会出现元素被裁切
- 所有主题变量集中在 `src/assets/main.css` 的 `:root`

## 开发

```sh
npm install
npm run dev      # http://localhost:5173
npm run build    # 类型检查 + 生产构建
npm run preview  # 预览构建产物
```

后续接入真实内容时，在 `src/views/` 下新建对应页面并替换 `router/index.ts` 里的 component 即可；
建议同步补充 `src/api/`、`src/types/` 与登录态守卫（目前仅用 `sessionStorage` 记录登录状态，未强制拦截）。
