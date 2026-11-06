<script setup lang="ts">
// 引入 Element Plus 提示、日期类型
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
// 统一请求工具
import request from '@/utils/request'

// 实验室卡片数据（来自 /lab/available）
const loading = ref(false)
const labs = ref<any[]>([])

// —— 预约弹窗相关 ——
const dialogVisible = ref(false) // 弹窗显示
const currentLab = ref<any>(null) // 当前正在预约的实验室
const devices = ref<any[]>([])    // 该实验室下的设备选项
const submitting = ref(false)     // 提交中

// 预约表单
const form = reactive({
  appoint_date: '', // 预约日期 "YYYY-MM-DD"
  start_time: '',   // 开始时间 "HH:mm:ss"
  end_time: '',     // 结束时间 "HH:mm:ss"
  device_id: '' as number | '' | null, // 设备（可留空表示不指定）
  purpose: '',      // 用途
})

// 表单校验：日期、起止时间、用途必填
const formRef = ref<FormInstance>()
const rules: FormRules = {
  appoint_date: [{ required: true, message: '请选择预约日期', trigger: 'change' }],
  start_time: [{ required: true, message: '请选择开始时间', trigger: 'change' }],
  end_time: [{ required: true, message: '请选择结束时间', trigger: 'change' }],
  purpose: [{ required: true, message: '请输入用途', trigger: 'blur' }],
}

// 实验室状态映射（仅启用实验室会被返回，这里做兜底展示）
function labStatusMeta(s: number): { text: string; type: 'success' | 'info' } {
  if (s === 1) return { text: '启用', type: 'success' }
  return { text: '停用', type: 'info' }
}

// 禁止选择今天之前的日期（el-date-picker 的 disabled-date）
function disabledDate(date: Date): boolean {
  // 今天的 0 点；小于今天则禁用
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  return date.getTime() < today.getTime()
}

// 拉取可预约实验室列表
async function fetchLabs() {
  loading.value = true
  try {
    const data: any = await request.get('/lab/available')
    labs.value = data || []
  } catch (e) {
    // 拦截器已弹错
  } finally {
    loading.value = false
  }
}

// 点击卡片「预约」：记录当前实验室，拉该实验室设备，打开弹窗并重置表单
async function openBook(lab: any) {
  currentLab.value = lab
  Object.assign(form, {
    appoint_date: '', start_time: '', end_time: '', device_id: '', purpose: '',
  })
  try {
    const data: any = await request.get(`/lab/${lab.id}/devices`)
    devices.value = data || []
  } catch (e) {
    // 拦截器已弹错，但弹窗仍打开
    devices.value = []
  }
  dialogVisible.value = true
}

// 提交预约：POST /appointment
async function handleSubmit() {
  if (!formRef.value || !currentLab.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    await request.post('/appointment', {
      lab_id: currentLab.value.id,
      device_id: form.device_id ? form.device_id : null, // 空表示不指定设备
      appoint_date: form.appoint_date,
      start_time: form.start_time,
      end_time: form.end_time,
      purpose: form.purpose,
    })
    ElMessage.success('预约提交成功，等待审核')
    dialogVisible.value = false
    fetchLabs() // 刷新卡片（设备数等可能变化，顺手刷）
  } catch (e) {
    // 拦截器已弹错（过去日期/时间重叠/实验室未启用等）
  } finally {
    submitting.value = false
  }
}

// 挂载拉取实验室
onMounted(() => {
  fetchLabs()
})
</script>

<template>
  <div class="page">
    <!-- 卡片网格：展示可预约实验室 -->
    <div class="grid" v-loading="loading">
      <div
        v-for="lab in labs"
        :key="lab.id"
        class="lab-card"
      >
        <div class="card-head">
          <span class="lab-name">{{ lab.name }}</span>
          <el-tag :type="labStatusMeta(lab.status).type" effect="light">
            {{ labStatusMeta(lab.status).text }}
          </el-tag>
        </div>
        <div class="card-body">
          <div class="meta-row"><span class="meta-label">位置</span>{{ lab.location || '—' }}</div>
          <div class="meta-row"><span class="meta-label">容量</span>{{ lab.capacity }}</div>
          <div class="meta-row"><span class="meta-label">设备数</span>{{ lab.device_count }}</div>
        </div>
        <div class="card-foot">
          <el-button type="primary" size="small" @click="openBook(lab)">预约</el-button>
        </div>
      </div>
      <!-- 空占位 -->
      <el-empty v-if="!loading && labs.length === 0" description="暂无可选实验室" />
    </div>

    <!-- 预约弹窗 -->
    <el-dialog v-model="dialogVisible" title="预约实验室" width="480px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="88px">
        <el-form-item label="实验室">
          <!-- 当前实验室名称（只读展示） -->
          <el-input :model-value="currentLab?.name" disabled />
        </el-form-item>
        <el-form-item label="日期" prop="appoint_date">
          <el-date-picker
            v-model="form.appoint_date"
            type="date"
            placeholder="选择日期"
            value-format="YYYY-MM-DD"
            :disabled-date="disabledDate"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="开始时间" prop="start_time">
          <el-time-picker
            v-model="form.start_time"
            placeholder="开始时间"
            value-format="HH:mm:ss"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="结束时间" prop="end_time">
          <el-time-picker
            v-model="form.end_time"
            placeholder="结束时间"
            value-format="HH:mm:ss"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="设备">
          <el-select
            v-model="form.device_id"
            placeholder="不指定设备"
            clearable
            style="width: 100%"
          >
            <el-option
              v-for="d in devices"
              :key="d.id"
              :label="`${d.name} (${d.code})`"
              :value="d.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="用途" prop="purpose">
          <el-input v-model="form.purpose" type="textarea" :rows="3" placeholder="请输入用途" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">
          提交预约
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.page {
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 20px 22px;
  box-shadow: 0 6px 20px -12px rgba(31, 45, 80, 0.18);
}
/* 卡片网格：自适应列数 */
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 16px;
}
.lab-card {
  display: flex;
  flex-direction: column;
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 16px 18px;
  background: #fff;
  transition: box-shadow 0.18s, transform 0.18s;
}
.lab-card:hover {
  box-shadow: 0 6px 20px -12px rgba(31, 45, 80, 0.18);
  transform: translateY(-2px);
}
.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.lab-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-1);
}
.card-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex: 1;
}
.meta-row {
  font-size: 13px;
  color: var(--text-2);
}
.meta-label {
  display: inline-block;
  width: 48px;
  color: var(--text-3);
}
.card-foot {
  margin-top: 14px;
  text-align: right;
}
</style>
