<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock, ArrowRight } from '@element-plus/icons-vue'
import request from '@/utils/request'
// 导入用户状态仓库：登录成功后把后端返回的 user 写进去，头部/个人中心就能同步
import { setUser } from '@/stores/user'

const router = useRouter()

// 登录框默认留空，不再预填演示账号
const username = ref('')
const password = ref('')
const remember = ref(true)
const loading = ref(false)

const handleLogin = async () => {
  if (!username.value.trim() || !password.value.trim()) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  loading.value = true
  try {
    // 调用后端登录接口；request 已带 /api，所以这里只写 /auth/login
    // 用 any 是为了简单：拦截器已经把数据拆好成 { token, user } 了
    const data: any = await request.post('/auth/login', {
      username: username.value.trim(),
      password: password.value,
    })
    // 把 token 存起来，下次请求会自动带上
    localStorage.setItem('token', data.token)
    // 把后端返回的用户信息写进全局 store（单数据源）：头部、个人中心都会跟着变
    setUser(data.user)
    ElMessage.success('登录成功，欢迎回来')
    await router.push('/home')
  } catch (e) {
    // 密码错误时，拦截器已经弹过提示了，这里不重复弹，只负责停掉 loading
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <!-- 背景装饰层：独立于内容，只裁剪装饰，不裁剪页面 -->
    <div class="bg-layer" aria-hidden="true">
      <span class="glow glow-a"></span>
      <span class="glow glow-b"></span>
      <span class="glow glow-c"></span>
      <span class="grid"></span>
      <span class="ring ring-a"></span>
      <span class="ring ring-b"></span>
      <span class="band"></span>
    </div>

    <!-- 第一层：页面顶部品牌栏 -->
    <header class="login-header">
      <div class="lh-brand">
        <span class="lh-logo">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="#fff"
            stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M9 3h6" />
            <path d="M10 3v5.3L5.7 17A2.3 2.3 0 0 0 7.8 20.4h8.4a2.3 2.3 0 0 0 2.1-3.4L14 8.3V3" />
            <path d="M7.3 14.6h9.4" />
          </svg>
        </span>
        <span class="lh-name">智能实验室预约系统</span>
        <span class="lh-en">LAB RESERVATION</span>
      </div>
      <div class="lh-extra">
        <span class="lh-status"><i></i>系统运行正常</span>
        <span class="lh-divider"></span>
        <span class="lh-help">帮助中心</span>
      </div>
    </header>

    <!-- 第二层：居中的登录卡片 -->
    <main class="login-main">
      <div class="login-center">
        <section class="login-card">
          <div class="card-badge">
            <svg viewBox="0 0 24 24" width="26" height="26" fill="none" stroke="#fff"
              stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
              <path d="M9 3h6" />
              <path d="M10 3v5.3L5.7 17A2.3 2.3 0 0 0 7.8 20.4h8.4a2.3 2.3 0 0 0 2.1-3.4L14 8.3V3" />
              <path d="M7.3 14.6h9.4" />
            </svg>
          </div>

          <div class="card-head">
            <span class="eyebrow">WELCOME BACK</span>
            <h1>智能实验室预约系统</h1>
            <p>欢迎回来，请登录您的账号以继续使用</p>
          </div>

          <form class="login-form" autocomplete="off" @submit.prevent="handleLogin">
            <label class="field-label" for="login-user">用户名</label>
            <el-input
              id="login-user"
              v-model="username"
              :prefix-icon="User"
              placeholder="请输入用户名"
              clearable
              size="large"
              autocomplete="off"
            />

            <label class="field-label" for="login-pwd">密码</label>
            <el-input
              id="login-pwd"
              v-model="password"
              :prefix-icon="Lock"
              type="password"
              placeholder="请输入密码"
              show-password
              size="large"
              autocomplete="new-password"
            />

            <div class="form-row">
              <el-checkbox v-model="remember" label="记住我" />
              <button class="forgot" type="button" @click="ElMessage.info('请联系系统管理员重置密码')">
                忘记密码？
              </button>
            </div>

            <button class="login-btn" type="submit" :disabled="loading">
              <span>{{ loading ? '正在登录…' : '登 录' }}</span>
              <el-icon :size="16"><ArrowRight /></el-icon>
            </button>

            <!-- 登录按钮下方：没有账号去注册 -->
            <div class="to-login">
              <span>没有账号？</span>
              <button class="link-btn" type="button" @click="router.push('/register')">去注册</button>
            </div>
          </form>

          <!-- 演示账号提示：管理员与学生各一个 -->
          <p class="demo-hint">
            管理员：账号 <b>admin</b> · 密码 <b>admin</b><br />
            学生：账号 <b>student01</b> · 密码 <b>123456</b>
          </p>
        </section>

        <p class="copyright">© 2026 智能实验室预约系统　|　仅限校内网络访问</p>
      </div>
    </main>
  </div>
</template>

<style scoped>
/* ============ 页面底层 ============ */
.login-page {
  position: relative;
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background:
    radial-gradient(900px 520px at 12% 8%, rgba(255, 255, 255, 0.95), transparent 70%),
    radial-gradient(800px 620px at 88% 92%, rgba(203, 222, 255, 0.7), transparent 72%),
    linear-gradient(135deg, #f7faff 0%, #eef4ff 48%, #e6efff 100%);
  color: #1b2430;
}

.bg-layer {
  position: absolute;
  inset: 0;
  overflow: hidden;
  pointer-events: none;
  z-index: 0;
}
.glow {
  position: absolute;
  border-radius: 50%;
  filter: blur(70px);
  opacity: 0.55;
}
.glow-a {
  width: 420px;
  height: 420px;
  top: -150px;
  right: -90px;
  background: #b9d1ff;
}
.glow-b {
  width: 380px;
  height: 380px;
  bottom: -160px;
  left: -110px;
  background: #a9c6ff;
}
.glow-c {
  width: 260px;
  height: 260px;
  top: 42%;
  left: 8%;
  background: #dce8ff;
  opacity: 0.6;
}
.grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(83, 128, 214, 0.055) 1px, transparent 1px),
    linear-gradient(90deg, rgba(83, 128, 214, 0.055) 1px, transparent 1px);
  background-size: 42px 42px;
  mask-image: radial-gradient(ellipse at 50% 45%, #000 20%, transparent 78%);
}
.ring {
  position: absolute;
  border-radius: 50%;
  border: 1px solid rgba(80, 125, 210, 0.14);
}
.ring-a {
  width: 320px;
  height: 320px;
  top: -130px;
  left: 6%;
}
.ring-b {
  width: 210px;
  height: 210px;
  bottom: -80px;
  right: 8%;
  border-color: rgba(80, 125, 210, 0.18);
}
.band {
  position: absolute;
  width: 140%;
  height: 220px;
  left: -20%;
  bottom: -120px;
  transform: rotate(-6deg);
  background: linear-gradient(90deg, rgba(255, 255, 255, 0.5), rgba(255, 255, 255, 0.05));
  border-radius: 50%;
}

/* ============ 顶部品牌栏 ============ */
.login-header {
  position: relative;
  z-index: 2;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 18px clamp(20px, 4vw, 56px);
}
.lh-brand {
  display: flex;
  align-items: center;
  gap: 10px;
}
.lh-logo {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border-radius: 10px;
  background: linear-gradient(135deg, #4b86ff, #1f4fd6);
  box-shadow: 0 8px 18px -8px rgba(43, 108, 246, 0.9);
}
.lh-name {
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 0.4px;
  color: #1b2a44;
}
.lh-en {
  padding-left: 10px;
  border-left: 1px solid #cbd7ee;
  font-size: 10px;
  letter-spacing: 1.4px;
  color: #8a9ab4;
}
.lh-extra {
  display: flex;
  align-items: center;
  gap: 14px;
  font-size: 12.5px;
  color: #7c8ba4;
}
.lh-status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.lh-status i {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #16c090;
  box-shadow: 0 0 0 3px rgba(22, 192, 144, 0.14);
}
.lh-divider {
  width: 1px;
  height: 14px;
  background: #cdd8ea;
}
.lh-help {
  cursor: pointer;
}
.lh-help:hover {
  color: #2b6cf6;
}

/* ============ 中间层：卡片垂直 + 水平居中 ============ */
/* 用 flex + margin:auto 居中：内容超高时自动改为顶部对齐，
   不会出现 grid 居中把上半部分顶出视口而无法滚动的「割切」 */
.login-main {
  position: relative;
  z-index: 2;
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: clamp(24px, 4vh, 44px) 20px clamp(20px, 3vh, 32px);
}
.login-center {
  width: min(100%, 428px);
  margin: auto;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

/* 卡片 */
.login-card {
  position: relative;
  width: 100%;
  padding: 44px clamp(24px, 3vw, 36px) 24px;
  border: 1px solid rgba(226, 234, 248, 0.95);
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow:
    0 2px 4px rgba(30, 60, 120, 0.03),
    0 18px 48px -20px rgba(38, 78, 160, 0.28),
    0 60px 110px -70px rgba(31, 70, 150, 0.42);
  backdrop-filter: blur(10px);
}
.login-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 12%;
  right: 12%;
  height: 3px;
  border-radius: 0 0 4px 4px;
  background: linear-gradient(90deg, transparent, #6f9bff 30%, #2b6cf6 50%, #6f9bff 70%, transparent);
  opacity: 0.85;
}
.card-badge {
  position: absolute;
  top: -30px;
  left: 50%;
  transform: translateX(-50%);
  display: grid;
  place-items: center;
  width: 60px;
  height: 60px;
  border-radius: 19px;
  background: linear-gradient(140deg, #5b91ff 0%, #2b6cf6 52%, #1f4fd6 100%);
  border: 4px solid #fff;
  box-shadow: 0 14px 26px -12px rgba(43, 108, 246, 0.85);
}

/* 标题层次 */
.card-head {
  text-align: center;
}
.eyebrow {
  display: inline-block;
  padding: 3px 10px;
  border-radius: 20px;
  background: #eef4ff;
  color: #4b7ae0;
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 1.6px;
}
.card-head h1 {
  margin: 10px 0 5px;
  font-size: clamp(22px, 2.4vw, 26px);
  font-weight: 700;
  letter-spacing: 1px;
  color: #17233a;
}
.card-head p {
  margin: 0;
  font-size: 13px;
  color: #8a97ab;
}

/* 表单 */
.login-form {
  margin-top: 20px;
  display: flex;
  flex-direction: column;
}
.field-label {
  margin: 0 0 7px;
  font-size: 12.5px;
  font-weight: 600;
  color: #4a5668;
}
.field-label:not(:first-child) {
  margin-top: 14px;
}
.login-form :deep(.el-input__wrapper) {
  min-height: 46px;
  padding: 0 12px;
  border-radius: 10px;
  background: #fff;
  box-shadow: 0 0 0 1px #e3eaf6 inset;
  transition: box-shadow 0.2s, background 0.2s;
}
.login-form :deep(.el-input__wrapper:hover) {
  background: #fff;
  box-shadow: 0 0 0 1px #c9d8f2 inset;
}
.login-form :deep(.el-input__wrapper.is-focus) {
  background: #fff;
  box-shadow: 0 0 0 1px #2b6cf6 inset, 0 0 0 3px rgba(43, 108, 246, 0.12);
}
.login-form :deep(.el-input__inner) {
  font-size: 14px;
  color: #1b2430;
}
.login-form :deep(.el-input__prefix-inner > .el-icon) {
  font-size: 16px;
  color: #94a3ba;
}

/* 去掉浏览器自动填充时的蓝色底色（Chrome / Edge 的 -webkit-autofill） */
.login-form :deep(.el-input__inner:-webkit-autofill),
.login-form :deep(.el-input__inner:-webkit-autofill:hover),
.login-form :deep(.el-input__inner:-webkit-autofill:focus) {
  -webkit-box-shadow: 0 0 0 1000px #fff inset !important;
  -webkit-text-fill-color: #1b2430 !important;
  transition: background-color 5000s ease-in-out 0s !important;
}

.form-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: 14px 0 18px;
}
.form-row :deep(.el-checkbox__label) {
  font-size: 12.5px;
  color: #6b7891;
}
.forgot {
  padding: 0;
  border: 0;
  background: none;
  font-size: 12.5px;
  color: #2b6cf6;
  cursor: pointer;
}
.forgot:hover {
  text-decoration: underline;
}

.login-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: 100%;
  height: 46px;
  border: 0;
  border-radius: 10px;
  background: linear-gradient(100deg, #3f7bfa 0%, #2b6cf6 55%, #1f57df 100%);
  color: #fff;
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 3px;
  cursor: pointer;
  box-shadow: 0 10px 22px -10px rgba(43, 108, 246, 0.95);
  transition: transform 0.18s, box-shadow 0.18s, filter 0.18s;
}
.login-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 14px 26px -10px rgba(43, 108, 246, 0.95);
  filter: brightness(1.04);
}
.login-btn:active:not(:disabled) {
  transform: translateY(0);
}
.login-btn:disabled {
  opacity: 0.7;
  cursor: wait;
}

/* 登录按钮下方：去注册链接 */
.to-login {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  margin-top: 14px;
  font-size: 12.5px;
  color: #8a97ab;
}
.link-btn {
  padding: 0;
  border: 0;
  background: none;
  font-size: 12.5px;
  color: #2b6cf6;
  cursor: pointer;
}
.link-btn:hover {
  text-decoration: underline;
}

/* 演示账号提示：登录表单下方，管理员与学生各一行 */
.demo-hint {
  margin: 14px 0 0;
  text-align: center;
  font-size: 12.5px;
  line-height: 1.9;
  color: #8a97ab;
}
.demo-hint b {
  color: #2b6cf6;
  font-weight: 600;
}

.copyright {
  margin: 0;
  text-align: center;
  font-size: 11.5px;
  color: #93a1b8;
}

/* ============ 自适应：确保任何尺寸都不被裁切 ============ */
@media (max-width: 640px) {
  .login-header {
    padding: 14px 18px;
  }
  .lh-en,
  .lh-extra {
    display: none;
  }
  .login-main {
    padding: 44px 16px 22px;
  }
  .login-card {
    padding: 42px 20px 20px;
    border-radius: 18px;
  }
  .card-head h1 {
    font-size: 22px;
  }
  .copyright {
    font-size: 10.5px;
  }
}

@media (max-height: 780px) {
  .login-header {
    padding-top: 12px;
    padding-bottom: 12px;
  }
  .login-main {
    padding-top: 40px;
    padding-bottom: 16px;
  }
  .login-center {
    gap: 10px;
  }
  .login-card {
    padding-top: 40px;
    padding-bottom: 18px;
  }
  .card-head h1 {
    margin-top: 7px;
    font-size: 22px;
  }
  .login-form {
    margin-top: 16px;
  }
  .field-label:not(:first-child) {
    margin-top: 10px;
  }
  .form-row {
    margin: 10px 0 14px;
  }
  .to-login {
    margin-top: 10px;
  }
}
</style>
