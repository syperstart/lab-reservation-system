<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Loading, Plus } from '@element-plus/icons-vue'
import request from '@/utils/request'
// 导入用户状态单数据源：头像/姓名/邮箱全部从这里读，与右上角保持同一份数据
import { userState, setUser, updateUser, userInitial } from '@/stores/user'

// 可编辑的表单字段：账号/角色只读展示（直接读 userState），这里只保存可改的三项
const form = reactive({
  name: '',    // 名称
  email: '',   // 邮箱
  phone: '',   // 手机号
})

const saving = ref(false)     // 点击「保存修改」时
const uploading = ref(false)  // 上传头像时

// 进入页面：拉取最新个人信息并写进全局 store（保证刷新/多端一致），再预填表单
onMounted(async () => {
  try {
    const data: any = await request.get('/user/info')
    // 整体写入 store：头部、这里都会同步
    setUser(data)
    // 用 store 里的最新值预填可编辑表单
    form.name = userState.name || ''
    form.email = userState.email || ''
    form.phone = userState.phone || ''
  } catch (e) {
    // 拦截器已弹错误提示
  }
})

// 点击头像触发隐藏的文件选择框
const fileInput = ref<HTMLInputElement>()
const pickAvatar = () => fileInput.value?.click()

// 选择图片后：上传到后端，拿到 /uploads/... 链接，直接更新 store（头部立即同步）
const onFileChange = async (e: Event) => {
  const target = e.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return
  uploading.value = true
  try {
    const fd = new FormData()
    fd.append('file', file)
    fd.append('category', 'avatar')
    const res: any = await request.post('/upload', fd)
    // 写入全局 store：头像地址一变，右上角和本页头像同时更新，无需刷新
    updateUser({ avatar: res.url })
    ElMessage.success('头像已更新，记得点保存修改')
  } catch (err) {
    // 上传失败由拦截器弹提示
  } finally {
    uploading.value = false
    target.value = '' // 清空选择，保证同一文件能再次选
  }
}

// 保存修改：把可改字段写回 store 并请求后端持久化
const handleSave = async () => {
  if (!form.name.trim()) {
    ElMessage.warning('名称不能为空')
    return
  }
  saving.value = true
  try {
    const data: any = await request.put('/user/info', {
      name: form.name,
      email: form.email,
      phone: form.phone,
    })
    // 用后端返回的最新数据刷新 store（后端可能规范化了空格等）
    updateUser({
      name: data.name,
      email: data.email || '',
      phone: data.phone || '',
    })
    ElMessage.success('更新成功')
  } catch (e) {
    // 拦截器已弹错误提示
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="profile-page">
    <div class="profile-card">
      <h2 class="card-title">个人信息</h2>

      <!-- 头像区：点击可上传新头像；无头像显示姓名首字的圆形色块 -->
      <div class="avatar-block">
        <div class="avatar-wrap" @click="pickAvatar" title="点击更换头像">
          <img v-if="userState.avatar" :src="userState.avatar" class="avatar-img" alt="头像" />
          <span v-else class="avatar-img default-avatar">{{ userInitial() }}</span>
          <div class="avatar-mask">
            <el-icon><Plus /></el-icon>
            <span>更换</span>
          </div>
        </div>
        <!-- 真正的文件选择框，隐藏起来 -->
        <input ref="fileInput" type="file" accept="image/*" hidden @change="onFileChange" />
        <p class="avatar-tip">点击头像可上传新图片（支持 jpg/png/gif/webp，≤5MB）</p>
      </div>

      <!-- 表单：账号/角色只读，其余可编辑；grid 布局收紧、不溢出 -->
      <div class="form-list">
        <div class="form-row">
          <label class="label">账号</label>
          <el-input v-model="userState.username" disabled placeholder="账号" />
        </div>

        <div class="form-row">
          <label class="label">名称</label>
          <el-input v-model="form.name" placeholder="请输入名称" clearable />
        </div>

        <div class="form-row">
          <label class="label">角色</label>
          <el-input v-model="userState.role" disabled placeholder="角色" />
        </div>

        <div class="form-row email-row">
          <label class="label">邮箱</label>
          <el-input v-model="form.email" placeholder="请输入邮箱" clearable />
        </div>

        <div class="form-row">
          <label class="label">手机号</label>
          <el-input v-model="form.phone" placeholder="请输入手机号" clearable maxlength="11" />
        </div>

        <div class="form-actions">
          <el-button type="primary" :loading="saving" @click="handleSave">
            {{ saving ? '保存中…' : '保存修改' }}
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 卡片收紧：限宽居中、内边距合理，避免大留白 */
.profile-page {
  max-width: 720px;
  margin: 0 auto;
}
.profile-card {
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 24px 28px;
  box-shadow: 0 6px 20px -12px rgba(31, 45, 80, 0.18);
}
.card-title {
  margin: 0 0 18px;
  font-size: 18px;
  font-weight: 700;
  color: #131a24;
}

/* 头像区：高度收住，提示文字小号灰 */
.avatar-block {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: 20px;
}
.avatar-wrap {
  position: relative;
  width: 88px;
  height: 88px;
  border-radius: 50%;
  overflow: hidden;
  cursor: pointer;
  border: 2px solid var(--line);
}
.avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.avatar-img.default-avatar {
  display: grid;
  place-items: center;
  color: #fff;
  font-size: 26px;
  font-weight: 600;
  background: linear-gradient(135deg, #6f9bff, #2b6cf6);
}
.avatar-mask {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  background: rgba(0, 0, 0, 0.45);
  color: #fff;
  font-size: 12px;
  opacity: 0;
  transition: opacity 0.2s;
}
.avatar-wrap:hover .avatar-mask {
  opacity: 1;
}
.avatar-tip {
  margin: 8px 0 0;
  font-size: 12px;
  color: var(--text-3);
}

/* 表单：grid 两列，标签固定 88px，值列自适应；输入框 100% 不写死 */
.form-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.form-row {
  display: grid;
  grid-template-columns: 88px 1fr;
  align-items: center;
  column-gap: 16px;
}
.label {
  font-size: 14px;
  color: #4d596b;
  text-align: right;
}
.form-row :deep(.el-input) {
  width: 100%;
}

.form-actions {
  margin-top: 6px;
}

/* 小屏（< 900px）：隐藏邮箱行，只留头像 + 姓名，避免挤压 */
@media (max-width: 900px) {
  .email-row {
    display: none;
  }
  .form-row {
    grid-template-columns: 72px 1fr;
    column-gap: 10px;
  }
}
</style>
