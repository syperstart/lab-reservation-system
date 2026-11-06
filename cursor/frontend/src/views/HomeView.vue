<script setup lang="ts">
// ==================== 系统首页 ====================
// 目标：不再用占位组件，首页直接展示「欢迎语 + 个人信息概览 + 快捷入口」
// 数据来源：全局用户状态 store（登录时写入、刷新时从 localStorage 恢复），
//          所以不需要先点「个人中心」才有数据。
// =================================================

import { computed } from 'vue'
import { useRouter } from 'vue-router'
// 全局用户状态：头像/账号/姓名/角色/邮箱/手机号都从这里读
import { userState, userInitial } from '@/stores/user'

const router = useRouter()

// 角色展示文案
const roleText = computed(() => (userState.role === 'admin' ? '管理员' : '学生'))

// 快捷入口：按角色给出不同功能，点一下直接跳转
const shortcuts = computed(() =>
  userState.role === 'admin'
    ? [
        { label: '实验室管理', desc: '维护实验室信息', path: '/laboratory' },
        { label: '设备列表管理', desc: '维护各实验室设备', path: '/device' },
        { label: '预约审核', desc: '审核学生提交的预约', path: '/appointment' },
        { label: '账号管理', desc: '查看系统全部账号', path: '/accounts' },
      ]
    : [
        { label: 'AI智能助手', desc: '预约流程、常见问题随时问', path: '/assistant' },
        { label: '实验室列表', desc: '查看实验室与设备并预约', path: '/student/labs' },
        { label: '我的预约', desc: '查看预约状态与取消', path: '/student/my-appointments' },
      ],
)

// 个人信息字段（只读展示，账号/角色不可改）
const infoFields = computed(() => [
  { label: '账号', value: userState.username || '-' },
  { label: '姓名', value: userState.name || '-' },
  { label: '角色', value: roleText.value },
  { label: '邮箱', value: userState.email || '-' },
  { label: '手机号', value: userState.phone || '-' },
])
</script>

<template>
  <div class="home-page">
    <!-- 欢迎条：头像 + 姓名 -->
    <div class="welcome-card">
      <div class="welcome-avatar">
        <img v-if="userState.avatar" :src="userState.avatar" alt="头像" />
        <span v-else>{{ userInitial() }}</span>
      </div>
      <div class="welcome-text">
        <h2>欢迎回来，{{ userState.name || userState.username || '同学' }}</h2>
        <p>今天也可以安排一次实验室预约</p>
      </div>
    </div>

    <!-- 个人信息概览 -->
    <div class="info-card">
      <div class="card-head">
        <h3>个人信息</h3>
        <el-button type="primary" plain size="small" @click="router.push('/profile')">
          去个人中心修改
        </el-button>
      </div>
      <div class="info-grid">
        <div v-for="f in infoFields" :key="f.label" class="info-item">
          <label>{{ f.label }}</label>
          <span :title="f.value">{{ f.value }}</span>
        </div>
      </div>
    </div>

    <!-- 快捷入口 -->
    <div class="shortcut-grid">
      <div
        v-for="s in shortcuts"
        :key="s.path"
        class="shortcut"
        @click="router.push(s.path)"
      >
        <b>{{ s.label }}</b>
        <span>{{ s.desc }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.home-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-width: 960px;
}

/* 欢迎条 */
.welcome-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 20px 24px;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 14px;
  box-shadow: 0 6px 20px -12px rgba(31, 45, 80, 0.18);
}
.welcome-avatar {
  flex-shrink: 0;
  display: grid;
  place-items: center;
  width: 52px;
  height: 52px;
  border-radius: 50%;
  overflow: hidden;
  color: #fff;
  font-size: 20px;
  font-weight: 600;
  background: linear-gradient(135deg, #6f9bff, #2b6cf6);
}
.welcome-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.welcome-text h2 {
  margin: 0 0 4px;
  font-size: 18px;
  color: #131a24;
}
.welcome-text p {
  margin: 0;
  font-size: 13px;
  color: var(--text-3);
}

/* 个人信息卡片 */
.info-card {
  padding: 18px 24px 22px;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 14px;
  box-shadow: 0 6px 20px -12px rgba(31, 45, 80, 0.18);
}
.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}
.card-head h3 {
  margin: 0;
  font-size: 15px;
  color: #131a24;
}
.info-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px 24px;
}
.info-item {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}
.info-item label {
  flex-shrink: 0;
  width: 56px;
  font-size: 13px;
  color: var(--text-3);
}
.info-item span {
  min-width: 0;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  font-size: 14px;
  color: #1f2329;
}

/* 快捷入口 */
.shortcut-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
}
.shortcut {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 16px 18px;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.18s;
}
.shortcut:hover {
  border-color: #b9cdf7;
  box-shadow: 0 8px 22px -14px rgba(43, 108, 246, 0.55);
  transform: translateY(-1px);
}
.shortcut b {
  font-size: 14px;
  color: #1f2329;
}
.shortcut span {
  font-size: 12.5px;
  color: var(--text-3);
}

/* 小屏：信息两列变一列 */
@media (max-width: 640px) {
  .info-grid {
    grid-template-columns: 1fr;
  }
}
</style>
