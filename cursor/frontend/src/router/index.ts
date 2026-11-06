import { createRouter, createWebHistory } from 'vue-router'
import BasicLayout from '@/layouts/BasicLayout.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { title: '登录', fullTitle: '智能实验室预约系统' },
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('@/views/RegisterView.vue'),
      meta: { title: '注册', fullTitle: '智能实验室预约系统' },
    },
    {
      path: '/',
      component: BasicLayout,
      redirect: '/login',
      children: [
        {
          path: 'home',
          name: 'home',
          component: () => import('@/views/HomeView.vue'),
          meta: { title: '系统首页' },
        },
        {
          path: 'laboratory',
          name: 'laboratory',
          component: () => import('@/views/LabManageView.vue'),
          meta: { title: '实验室管理', role: 'admin' },
        },
        {
          path: 'device',
          name: 'device',
          component: () => import('@/views/DeviceManageView.vue'),
          meta: { title: '设备列表管理', role: 'admin' },
        },
        {
          path: 'appointment',
          name: 'appointment',
          component: () => import('@/views/AppointmentReviewView.vue'),
          meta: { title: '预约审核', role: 'admin' },
        },
        {
          path: 'accounts',
          name: 'accounts',
          component: () => import('@/views/AccountsView.vue'),
          meta: { title: '账号管理', role: 'admin' },
        },
        {
          path: 'profile',
          name: 'profile',
          component: () => import('@/views/ProfileView.vue'),
          meta: { title: '个人信息' },
        },
        {
          path: 'assistant',
          name: 'assistant',
          component: () => import('@/views/AssistantView.vue'),
          meta: { title: 'AI智能助手' },
        },
        {
          path: 'student/labs',
          name: 'student-labs',
          component: () => import('@/views/StudentLabsView.vue'),
          meta: { title: '实验室列表' },
        },
        {
          path: 'student/my-appointments',
          name: 'student-my-appointments',
          component: () => import('@/views/StudentMyAppointmentsView.vue'),
          meta: { title: '我的预约' },
        },
      ],
    },
  ],
  scrollBehavior: () => ({ top: 0 }),
})

// 路由守卫：每次页面跳转前都会执行
router.beforeEach((to) => {
  const token = localStorage.getItem('token')
  // 免登录白名单：登录页、注册页不用 token 也能进
  const whitelist = ['/login', '/register']
  // 没登录 + 去的不是白名单页面 → 强制去登录页
  if (!token && !whitelist.includes(to.path)) {
    return { path: '/login' }
  }
  // 已登录 + 还想回登录页或注册页 → 直接进首页
  if (token && (to.path === '/login' || to.path === '/register')) {
    return { path: '/home' }
  }
  // 角色校验：标记了 role:'admin' 的页面，学生不能进（管理员专属）
  // 从 localStorage 里读当前用户角色（与后端 store 同源）
  if (to.meta.role === 'admin') {
    try {
      const user = JSON.parse(localStorage.getItem('user') || '{}')
      if (user.role !== 'admin') {
        // 学生误访问管理员页面 → 引导到学生自己的实验室列表
        return { path: '/student/labs' }
      }
    } catch (e) {
      return { path: '/student/labs' }
    }
  }
})

router.afterEach((to) => {
  const title = (to.meta.title as string) || '系统首页'
  document.title = (to.meta.fullTitle as string) || `${title} · 智能实验室预约系统`
})

export default router
