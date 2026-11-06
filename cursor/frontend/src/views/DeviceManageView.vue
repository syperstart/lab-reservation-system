<script setup lang="ts">
// 引入 Element Plus 提示与二次确认组件、表单类型、图标
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Search, Plus, Picture, Edit, Delete } from '@element-plus/icons-vue'
// 统一请求工具（拦截器已自动带 token）
import request from '@/utils/request'

// —— 筛选条件 ——
const labId = ref<number | ''>('')   // 按所属实验室筛选（来自 /lab/options）
const keyword = ref('')               // 设备名称关键字

// —— 列表数据状态 ——
const loading = ref(false)
const list = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)

// 实验室下拉选项（顶部筛选 & 弹窗内共用）
const labOptions = ref<any[]>([])

// —— 弹窗状态 ——
const dialogVisible = ref(false)
const dialogTitle = ref('新增设备')
const editingId = ref<number | null>(null)
const submitting = ref(false)

// 表单数据（与截图弹窗 7 个字段一致：实验室/名称/说明/图片/型号规格/数量/状态）
const form = reactive({
  lab_id: '' as number | '', // 所属实验室 id
  name: '',                  // 设备名称
  description: '',           // 说明
  image: '' as string,       // 图片 URL（上传后回填，可空）
  model: '',                 // 型号规格
  quantity: 1,               // 数量，默认 1
  status: 1,                 // 状态，默认 1 正常（0=维修）
})

// 表单校验规则：所属实验室、设备名称、数量必填
const formRef = ref<FormInstance>()
const rules: FormRules = {
  lab_id: [{ required: true, message: '请选择所属实验室', trigger: 'change' }],
  name: [{ required: true, message: '请输入设备名称', trigger: 'blur' }],
  quantity: [{ required: true, message: '请输入数量', trigger: 'change' }],
}

// 局部函数：设备状态数字 → { 文本, el-tag 类型 }
function deviceStatusMeta(s: number): { text: string; type: 'success' | 'warning' } {
  if (s === 1) return { text: '正常', type: 'success' }
  return { text: '维修', type: 'warning' }
}

// 拉取「启用中的实验室」选项，供下拉使用
async function fetchLabOptions() {
  try {
    const data: any = await request.get('/lab/options')
    labOptions.value = data || []
  } catch (e) {
    // 拦截器已弹错
  }
}

// 拉取设备列表
async function fetchList() {
  loading.value = true
  try {
    const data: any = await request.get('/device/list', {
      params: {
        page: page.value,
        page_size: pageSize.value,
        // 实验室 / 名称 为空（全部）时不传，避免把空串发给后端导致 422
        ...(labId.value !== '' ? { lab_id: labId.value } : {}),
        ...(keyword.value.trim() !== '' ? { name: keyword.value.trim() } : {}),
      },
    })
    list.value = data.list || []
    total.value = data.total || 0
  } catch (e) {
    // 拦截器已弹错
  } finally {
    loading.value = false
  }
}

// 查询按钮 / 回车：重置到第 1 页
function handleSearch() {
  page.value = 1
  fetchList()
}
// 分页
function handleCurrentChange(p: number) {
  page.value = p
  fetchList()
}
function handleSizeChange(s: number) {
  pageSize.value = s
  page.value = 1
  fetchList()
}

// 打开新增弹窗：清空表单
function openCreate() {
  editingId.value = null
  dialogTitle.value = '新增设备'
  Object.assign(form, {
    lab_id: '', name: '', description: '', image: '', model: '', quantity: 1, status: 1,
  })
  dialogVisible.value = true
}

// 打开编辑弹窗：拉详情回填
async function openEdit(row: any) {
  editingId.value = row.id
  dialogTitle.value = '编辑设备'
  try {
    const data: any = await request.get(`/device/${row.id}`)
    Object.assign(form, {
      lab_id: data.lab_id,
      name: data.name,
      description: data.description || '',
      image: data.image || '',
      model: data.model || '',
      quantity: data.quantity,
      status: data.status,
    })
    dialogVisible.value = true
  } catch (e) {
    // 拦截器已弹错
  }
}

// 提交：新增/编辑
async function handleSubmit() {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    if (editingId.value) {
      await request.put(`/device/${editingId.value}`, { ...form })
      ElMessage.success('保存成功')
    } else {
      await request.post('/device', { ...form })
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    fetchList()
  } catch (e) {
    // 拦截器已弹错
  } finally {
    submitting.value = false
  }
}

// 删除：二次确认
async function handleDelete(row: any) {
  try {
    await ElMessageBox.confirm(
      `确定要删除设备「${row.name}」吗？此操作不可恢复。`,
      '删除确认',
      { type: 'warning', confirmButtonText: '确定删除', cancelButtonText: '取消' },
    )
  } catch (e) {
    return
  }
  try {
    await request.delete(`/device/${row.id}`)
    ElMessage.success('已删除')
    fetchList()
  } catch (e) {
    // 拦截器已弹错（如「该设备存在未完成的预约，无法删除」）
  }
}

// —— 图片上传：复用 /api/upload，与个人信息页同一套 FormData + 拦截器带 token 的方式 ——
const fileInput = ref<HTMLInputElement>()
function pickImage() {
  fileInput.value?.click()
}
async function onImageChange(e: Event) {
  const target = e.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return
  try {
    const fd = new FormData()
    fd.append('file', file)
    fd.append('category', 'device') // 分类目录，便于区分头像等上传
    const res: any = await request.post('/upload', fd)
    // 返回 data.url 形如 /uploads/device/2026/11/05/xxx.png，可直接当 <img src>
    form.image = res.url
    ElMessage.success('图片已上传')
  } catch (err) {
    // 上传失败由拦截器弹提示
  } finally {
    target.value = '' // 清空选择，保证同一文件能再次选
  }
}
// 移除已上传图片
function removeImage() {
  form.image = ''
}

// 挂载：拉选项 + 拉列表
onMounted(() => {
  fetchLabOptions()
  fetchList()
})
</script>

<template>
  <div class="page">
    <!-- 工具栏：名称查询 + 实验室下拉 + 查询(蓝) + 新增(绿) -->
    <div class="toolbar">
      <el-input
        v-model="keyword"
        placeholder="请输入名称查询"
        clearable
        style="width: 200px"
        @keyup.enter="handleSearch"
        @clear="handleSearch"
      />
      <el-select
        v-model="labId"
        placeholder="请选择实验室"
        clearable
        style="width: 180px"
        @change="handleSearch"
      >
        <el-option
          v-for="opt in labOptions"
          :key="opt.id"
          :label="opt.name"
          :value="opt.id"
        />
      </el-select>
      <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
      <el-button type="success" :icon="Plus" @click="openCreate">新增</el-button>
    </div>

    <!-- 设备表格 -->
    <el-table :data="list" v-loading="loading" border stripe empty-text="暂无数据">
      <el-table-column prop="lab_name" label="所属实验室" min-width="130" align="center" />
      <el-table-column prop="name" label="设备名称" min-width="140" show-overflow-tooltip />
      <!-- 图片：56×40 缩略图，圆角；为空显示灰色占位图，点击可预览 -->
      <el-table-column label="图片" width="90" align="center">
        <template #default="{ row }">
          <el-image
            v-if="row.image"
            :src="row.image"
            :preview-src-list="[row.image]"
            :initial-index="0"
            preview-teleported
            fit="cover"
            style="width: 56px; height: 40px; border-radius: 6px; vertical-align: middle"
          />
          <div v-else class="img-placeholder">
            <el-icon><Picture /></el-icon>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="model" label="型号规格" min-width="120" show-overflow-tooltip />
      <el-table-column prop="quantity" label="数量" width="80" align="center" />
      <el-table-column label="状态" width="100" align="center">
        <template #default="{ row }">
          <el-tag :type="deviceStatusMeta(row.status).type" effect="light">
            {{ deviceStatusMeta(row.status).text }}
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

    <!-- 新增/编辑弹窗：7 个字段 -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="500px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="92px">
        <el-form-item label="所属实验室" prop="lab_id">
          <el-select v-model="form.lab_id" placeholder="请选择实验室" style="width: 100%">
            <el-option
              v-for="opt in labOptions"
              :key="opt.id"
              :label="opt.name"
              :value="opt.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="设备名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入设备名称" />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="请输入说明" />
        </el-form-item>
        <!-- 图片：点击上传，复用 /api/upload -->
        <el-form-item label="图片">
          <div class="upload-box" :class="{ 'has-img': form.image }" @click="pickImage">
            <img v-if="form.image" :src="form.image" class="preview" alt="设备图片" />
            <template v-else>
              <el-icon class="up-icon"><Plus /></el-icon>
              <span>上传图片</span>
            </template>
            <div v-if="form.image" class="up-mask">
              <el-icon><Edit /></el-icon><span>更换</span>
            </div>
          </div>
          <el-button
            v-if="form.image"
            class="remove-btn"
            type="danger"
            link
            :icon="Delete"
            @click.stop="removeImage"
          >移除</el-button>
          <input ref="fileInput" type="file" accept="image/*" hidden @change="onImageChange" />
        </el-form-item>
        <el-form-item label="型号规格">
          <el-input v-model="form.model" placeholder="请输入型号规格" />
        </el-form-item>
        <el-form-item label="数量" prop="quantity">
          <el-input-number v-model="form.quantity" :min="1" :max="9999" />
        </el-form-item>
        <el-form-item label="状态">
          <el-radio-group v-model="form.status">
            <el-radio :value="1">正常</el-radio>
            <el-radio :value="0">维修</el-radio>
          </el-radio-group>
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
.page {
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 20px 22px;
  box-shadow: 0 6px 20px -12px rgba(31, 45, 80, 0.18);
}
.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}
.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
/* 表格图片为空时的灰色占位块 */
.img-placeholder {
  width: 56px;
  height: 40px;
  margin: 0 auto;
  border-radius: 6px;
  background: #f0f2f5;
  color: #c0c4cc;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
}
/* 弹窗图片上传框 */
.upload-box {
  position: relative;
  width: 96px;
  height: 96px;
  border: 1px dashed var(--line, #dcdfe6);
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  color: #8a94a6;
  cursor: pointer;
  overflow: hidden;
  background: #fafbfc;
}
.upload-box .up-icon {
  font-size: 22px;
}
.upload-box .preview {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.upload-box .up-mask {
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
.upload-box.has-img:hover .up-mask {
  opacity: 1;
}
.remove-btn {
  margin-left: 12px;
  vertical-align: top;
}
</style>
