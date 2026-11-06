<script setup lang="ts">
// 引入 Element Plus 提示组件（成功/警告提示）与二次确认弹窗
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
// 引入统一请求工具（拦截器已处理错误提示）
import request from '@/utils/request'
// 引入用户状态单数据源（此处主要演示从 store 读取，未强制使用，但保留引用以便后续扩展）
import { userState } from '@/stores/user'

// —— 列表查询的筛选条件 ——
const keyword = ref('')          // 关键字输入框（按名称/编号模糊搜索）
const filterStatus = ref<number | ''>('') // 状态筛选：''=全部 / 1=启用 / 0=停用

// —— 列表数据相关状态 ——
const loading = ref(false)       // 表格加载中
const list = ref<any[]>([])      // 实验室列表数据
const total = ref(0)             // 总数（分页用）
const page = ref(1)              // 当前页码
const pageSize = ref(10)         // 每页条数

// —— 弹窗（新增/编辑）相关状态 ——
const dialogVisible = ref(false) // 弹窗是否显示
const dialogTitle = ref('新增实验室') // 弹窗标题（随新增/编辑切换）
const editingId = ref<number | null>(null) // 正在编辑的 id；null 表示新增
const submitting = ref(false)    // 提交按钮 loading，防止重复提交

// 表单数据（新增/编辑共用同一对象）
const form = reactive({
  name: '',        // 名称
  code: '',        // 编号
  location: '',    // 位置
  capacity: 0,     // 容量
  description: '', // 描述
  status: 1,       // 状态，默认启用
})

// 表单校验规则：名称、编号必填
const formRef = ref<FormInstance>()
const rules: FormRules = {
  name: [{ required: true, message: '请输入实验室名称', trigger: 'blur' }],
  code: [{ required: true, message: '请输入实验室编号', trigger: 'blur' }],
}

// 局部函数：把实验室状态数字映射成 { 文本, el-tag 类型 }
function labStatusMeta(s: number): { text: string; type: 'success' | 'info' } {
  if (s === 1) return { text: '启用', type: 'success' }
  return { text: '停用', type: 'info' }
}

// 拉取实验室列表：拼接分页 + 筛选参数，赋值给 list/total
async function fetchList() {
  loading.value = true
  try {
    const data: any = await request.get('/lab/list', {
      params: {
        page: page.value,
        page_size: pageSize.value,
        keyword: keyword.value,
        // 状态为空（全部）时不传该参数，避免把空串发给后端导致 422
        ...(filterStatus.value !== '' ? { status: filterStatus.value } : {}),
      },
    })
    list.value = data.list || []
    total.value = data.total || 0
  } catch (e) {
    // 拦截器已弹出错误提示，这里无需额外处理
  } finally {
    loading.value = false
  }
}

// 查询按钮 / 筛选变化：回到第一页重新拉取
function handleSearch() {
  page.value = 1
  fetchList()
}

// 分页：页码变化
function handleCurrentChange(p: number) {
  page.value = p
  fetchList()
}
// 分页：每页条数变化
function handleSizeChange(s: number) {
  pageSize.value = s
  page.value = 1
  fetchList()
}

// 打开「新增」弹窗：清空表单、重置编辑 id
function openCreate() {
  editingId.value = null
  dialogTitle.value = '新增实验室'
  Object.assign(form, {
    name: '', code: '', location: '', capacity: 0, description: '', status: 1,
  })
  dialogVisible.value = true
}

// 打开「编辑」弹窗：先按 id 拉详情，回填表单
async function openEdit(row: any) {
  editingId.value = row.id
  dialogTitle.value = '编辑实验室'
  try {
    const data: any = await request.get(`/lab/${row.id}`)
    Object.assign(form, {
      name: data.name,
      code: data.code,
      location: data.location,
      capacity: data.capacity,
      description: data.description,
      status: data.status,
    })
    dialogVisible.value = true
  } catch (e) {
    // 拦截器已弹错
  }
}

// 提交：根据 editingId 判断新增(POST)还是编辑(PUT)
async function handleSubmit() {
  // 先触发表单校验，未通过直接返回
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    if (editingId.value) {
      // 编辑：PUT /lab/{id}，只传可改字段
      await request.put(`/lab/${editingId.value}`, { ...form })
      ElMessage.success('保存成功')
    } else {
      // 新增：POST /lab
      await request.post('/lab', { ...form })
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    fetchList() // 刷新列表
  } catch (e) {
    // 拦截器已弹错（例如该实验室下有设备时后端会返回 400）
  } finally {
    submitting.value = false
  }
}

// 删除：二次确认后 DELETE /lab/{id}
async function handleDelete(row: any) {
  try {
    await ElMessageBox.confirm(
      `确定要删除实验室「${row.name}」吗？此操作不可恢复。`,
      '删除确认',
      { type: 'warning', confirmButtonText: '确定删除', cancelButtonText: '取消' },
    )
  } catch (e) {
    // 用户点了取消，直接返回
    return
  }
  try {
    await request.delete(`/lab/${row.id}`)
    ElMessage.success('已删除')
    fetchList() // 刷新列表
  } catch (e) {
    // 拦截器已弹错（例如「请先移除该实验室下的设备」）
  }
}

// 页面挂载即拉取一次列表
onMounted(() => {
  fetchList()
})
</script>

<template>
  <div class="page">
    <!-- 顶部工具栏：关键字 + 状态筛选 + 新增按钮 -->
    <div class="toolbar">
      <el-input
        v-model="keyword"
        placeholder="搜索名称或编号"
        clearable
        style="width: 220px"
        @keyup.enter="handleSearch"
        @clear="handleSearch"
      />
      <el-select
        v-model="filterStatus"
        placeholder="状态"
        clearable
        style="width: 140px"
        @change="handleSearch"
      >
        <el-option label="全部" :value="''" />
        <el-option label="启用" :value="1" />
        <el-option label="停用" :value="0" />
      </el-select>
      <el-button type="primary" @click="openCreate">新增实验室</el-button>
    </div>

    <!-- 实验室表格 -->
    <el-table :data="list" v-loading="loading" border stripe>
      <el-table-column prop="code" label="编号" width="120" />
      <el-table-column prop="name" label="名称" min-width="140" />
      <el-table-column prop="location" label="位置" min-width="140" />
      <el-table-column prop="capacity" label="容量" width="100" align="center" />
      <el-table-column label="状态" width="100" align="center">
        <template #default="{ row }">
          <el-tag :type="labStatusMeta(row.status).type" effect="light">
            {{ labStatusMeta(row.status).text }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="160" align="center" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div class="pager">
      <el-pagination
        :current-page="page"
        :page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        @current-change="handleCurrentChange"
        @size-change="handleSizeChange"
      />
    </div>

    <!-- 新增/编辑弹窗 -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="480px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="88px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入实验室名称" />
        </el-form-item>
        <el-form-item label="编号" prop="code">
          <el-input v-model="form.code" placeholder="请输入实验室编号" />
        </el-form-item>
        <el-form-item label="位置">
          <el-input v-model="form.location" placeholder="请输入位置" />
        </el-form-item>
        <el-form-item label="容量">
          <el-input-number v-model="form.capacity" :min="0" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="3" placeholder="请输入描述" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="form.status" style="width: 100%">
            <el-option label="启用" :value="1" />
            <el-option label="停用" :value="0" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">
          确定
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
/* 内容区包裹：复用工件风格，卡片化视觉 */
.page {
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 20px 22px;
  box-shadow: 0 6px 20px -12px rgba(31, 45, 80, 0.18);
}
/* 工具栏：左对齐排列，右侧留白 */
.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}
/* 分页容器：靠右并留上边距 */
.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
