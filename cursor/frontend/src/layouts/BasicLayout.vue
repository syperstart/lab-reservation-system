<script setup lang="ts">
import { computed, markRaw } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  HomeFilled,
  OfficeBuilding,
  Monitor,
  User,
  Bell,
  ArrowDown,
  ArrowRight,
  SwitchButton,
  Setting,
  Calendar,
  ChatDotRound,
} from '@element-plus/icons-vue'
// 导入用户状态单数据源：头部展示的头像/姓名/邮箱全部从这里取，不再写死
import { userState, clearUser, userInitial } from '@/stores/user'

const route = useRoute()
const router = useRouter()

// 管理员菜单：系统首页 / 实验室管理 / 设备列表管理 / 预约审核 / 账号管理
const adminMenus = [
  { path: '/home', label: '系统首页', icon: markRaw(HomeFilled) },
  { path: '/laboratory', label: '实验室管理', icon: markRaw(OfficeBuilding) },
  { path: '/device', label: '设备列表管理', icon: markRaw(Monitor) },
  { path: '/appointment', label: '预约审核', icon: markRaw(Calendar) },
  // 账号管理：替换原来的「用户管理」占位页，避免菜单出现两个相似入口
  { path: '/accounts', label: '账号管理', icon: markRaw(User) },
]

// 学生菜单：系统首页 / AI智能助手 / 实验室列表 / 我的预约
const studentMenus = [
  { path: '/home', label: '系统首页', icon: markRaw(HomeFilled) },
  { path: '/assistant', label: 'AI智能助手', icon: markRaw(ChatDotRound) },
  { path: '/student/labs', label: '实验室列表', icon: markRaw(OfficeBuilding) },
  { path: '/student/my-appointments', label: '我的预约', icon: markRaw(Calendar) },
]

// 根据当前登录角色动态渲染菜单：全站只有 store 里的 userState 这一个数据源
const menus = computed(() =>
  userState.role === 'admin' ? adminMenus : studentMenus,
)

const isActive = (path: string) => route.path === path || route.path.startsWith(path + '/')
const currentLabel = computed(
  () => menus.value.find((m) => isActive(m.path))?.label ?? '系统首页',
)

const onCommand = (command: string) => {
  if (command === 'logout') {
    clearUser()                       // 清掉全局用户状态 + token + 本地存储（单数据源退出）
    router.push('/login')             // 回登录页
  } else if (command === 'profile') {
    router.push('/profile')            // 个人中心 → 个人信息页
  } else {
    ElMessage.info('功能建设中')
  }
}
</script>

<template>
  <div class="app-shell">
    <!-- 顶部栏 -->
    <header class="app-header">
      <div class="brand">
        <div class="brand-mark">
          <svg viewBox="0 0 24 24" width="19" height="19" fill="none" stroke="#fff"
            stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M9 3h6" />
            <path d="M10 3v5.3L5.7 17A2.3 2.3 0 0 0 7.8 20.4h8.4a2.3 2.3 0 0 0 2.1-3.4L14 8.3V3" />
            <path d="M7.3 14.6h9.4" />
          </svg>
        </div>
        <div class="brand-text">
          <span class="brand-title">智能实验室预约系统</span>
          <span class="brand-sub">Laboratory Reservation Platform</span>
        </div>
      </div>

      <div class="header-right">
        <button class="icon-btn" type="button" title="消息通知">
          <el-icon :size="18"><Bell /></el-icon>
          <span class="badge-dot"></span>
        </button>
        <span class="v-line"></span>
        <el-dropdown trigger="click" placement="bottom-end" @command="onCommand">
          <div class="user-chip">
            <!-- 有头像显示图片，没有则用姓名首字的圆形色块兜底（避免破图/空白） -->
            <img v-if="userState.avatar" :src="userState.avatar" class="top-avatar" alt="头像" />
            <span v-else class="top-avatar default-avatar">{{ userInitial() }}</span>
            <!-- 信息块：姓名 + 邮箱，过长统一省略号，不撑破布局 -->
            <span class="user-meta">
              <b class="ellipsis">{{ userState.name || userState.username }}</b>
              <em class="ellipsis">{{ userState.email || '未设置邮箱' }}</em>
            </span>
            <el-icon class="caret"><ArrowDown /></el-icon>
          </div>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item :icon="User" command="profile">个人中心</el-dropdown-item>
              <el-dropdown-item :icon="Setting" command="setting">系统设置</el-dropdown-item>
              <el-dropdown-item :icon="SwitchButton" command="logout" divided>退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </header>

    <div class="app-body">
      <!-- 侧边导航 -->
      <aside class="app-aside">
        <div class="nav-label">功能导航</div>
        <nav class="nav">
          <router-link
            v-for="m in menus"
            :key="m.path"
            :to="m.path"
            class="nav-item"
            :class="{ active: isActive(m.path) }"
          >
            <el-icon class="nav-icon"><component :is="m.icon" /></el-icon>
            <span class="nav-text">{{ m.label }}</span>
          </router-link>
        </nav>
      </aside>

      <!-- 主内容 -->
      <main class="app-main">
        <div class="crumb-bar">
          <el-icon class="crumb-icon"><HomeFilled /></el-icon>
          <span class="crumb-root">首页</span>
          <el-icon class="crumb-sep"><ArrowRight /></el-icon>
          <span class="crumb-current">{{ currentLabel }}</span>
        </div>
        <div class="page-scroll">
          <router-view v-slot="{ Component }">
            <transition name="fade-slide" mode="out-in">
              <component :is="Component" />
            </transition>
          </router-view>
        </div>
      </main>
    </div>
  </div>
</template>

<style scoped>
.app-shell {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  background: var(--bg);
}

/* ---------- 顶部栏 ---------- */
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 60px;
  padding: 0 20px 0 18px;
  background: #fff;
  border-bottom: 1px solid var(--line);
  z-index: 10;
}

.brand {
  display: flex;
  align-items: center;
  gap: 11px;
}
.brand-mark {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border-radius: 10px;
  background: linear-gradient(135deg, #4b86ff 0%, #2b6cf6 55%, #1f4fd6 100%);
  box-shadow: 0 6px 14px -6px rgba(43, 108, 246, 0.8);
}
.brand-text {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
}
.brand-title {
  font-size: 17px;
  font-weight: 600;
  letter-spacing: 0.4px;
  color: #131a24;
}
.brand-sub {
  font-size: 10px;
  letter-spacing: 0.6px;
  color: var(--text-3);
  text-transform: uppercase;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}
.icon-btn {
  position: relative;
  display: grid;
  place-items: center;
  width: 36px;
  height: 36px;
  border: 0;
  border-radius: 10px;
  background: transparent;
  color: var(--text-2);
  cursor: pointer;
  transition: all 0.18s;
}
.icon-btn:hover {
  background: var(--brand-50);
  color: var(--brand);
}
.badge-dot {
  position: absolute;
  top: 8px;
  right: 9px;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #ff5b5b;
  box-shadow: 0 0 0 2px #fff;
}
.v-line {
  width: 1px;
  height: 22px;
  background: var(--line);
}

.user-chip {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0; /* 关键：允许子元素在窄屏收缩，不撑破右侧容器 */
  padding: 4px 8px 4px 5px;
  border-radius: 10px;
  cursor: pointer;
  transition: background 0.18s;
}
.user-chip:hover {
  background: #f5f7fb;
}
/* 顶部头像：固定尺寸 + 圆形 + 不变形，永远不被挤压 */
.top-avatar {
  width: 36px;
  height: 36px;
  flex-shrink: 0;
  border-radius: 50%;
  object-fit: cover;
  background: #eef2f8;
}
/* 无头像兜底：姓名首字的圆形色块 */
.default-avatar {
  display: grid;
  place-items: center;
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  background: linear-gradient(135deg, #6f9bff, #2b6cf6);
}
/* 通用省略号：超长文本截断，保证布局不破 */
.ellipsis {
  display: block;
  max-width: 100%;
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.user-meta {
  display: flex;
  flex-direction: column;
  line-height: 1.25;
  max-width: 160px; /* 限制信息块宽度，配合 ellipsis 防止超长邮箱换行溢出 */
  min-width: 0;
}
.user-meta b {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-1);
}
.user-meta em {
  font-style: normal;
  font-size: 11px;
  color: var(--text-3);
}
.caret {
  color: var(--text-3);
  font-size: 12px;
}

/* ---------- 布局主体 ---------- */
.app-body {
  flex: 1;
  display: flex;
  min-height: 0;
}

/* ---------- 侧边栏 ---------- */
.app-aside {
  display: flex;
  flex-direction: column;
  width: 220px;
  flex-shrink: 0;
  padding: 14px 12px 16px;
  background: #fff;
  border-right: 1px solid var(--line);
}

.nav-label {
  padding: 6px 10px 10px;
  font-size: 11px;
  letter-spacing: 1px;
  color: #a9b3c2;
}

.nav {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.nav-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 10px;
  height: 42px;
  padding: 0 12px;
  border-radius: 10px;
  font-size: 14px;
  color: #4d596b;
  transition: all 0.18s ease;
}
.nav-item:hover {
  background: #f5f8ff;
  color: var(--brand);
}
.nav-icon {
  font-size: 17px;
  color: #8b97a8;
  transition: color 0.18s;
}
.nav-item:hover .nav-icon {
  color: var(--brand);
}
.nav-item.active {
  background: linear-gradient(90deg, #eaf1ff, #f3f7ff);
  color: var(--brand);
  font-weight: 600;
}
.nav-item.active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 18px;
  border-radius: 0 3px 3px 0;
  background: var(--brand);
}
.nav-item.active .nav-icon {
  color: var(--brand);
}

/* ---------- 主内容 ---------- */
.app-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.crumb-bar {
  display: flex;
  align-items: center;
  gap: 7px;
  height: 46px;
  padding: 0 24px;
  background: #fff;
  border-bottom: 1px solid var(--line);
  font-size: 12.5px;
  color: var(--text-3);
}
.crumb-icon {
  font-size: 14px;
  color: #b0bac8;
}
.crumb-sep {
  font-size: 10px;
  color: #c5ccd8;
}
.crumb-current {
  color: var(--text-1);
  font-weight: 500;
}

.page-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 22px 24px 32px;
}

/* 路由过渡 */
.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: all 0.2s ease;
}
.fade-slide-enter-from {
  opacity: 0;
  transform: translateY(8px);
}
.fade-slide-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

@media (max-width: 1100px) {
  .app-aside {
    width: 190px;
  }
  .brand-sub {
    display: none;
  }
}
</style>
