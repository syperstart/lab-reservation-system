<script setup lang="ts">
// 账号管理页（仅管理员可见）：查看系统所有账号的列表与详情，本期只读
import { ref, reactive, onMounted } from 'vue'
// 表单工具类型 + 图标：Search 查询按钮、RefreshLeft 重置按钮
import { Search, RefreshLeft } from '@element-plus/icons-vue'
// 统一请求工具（拦截器自动带 token；非 200 / 401 / 403 都会统一弹提示）
import request from '@/utils/request'

// —— 筛选条件 ——
const keyword = ref('')                  // 关键字：匹配账号或姓名
const filterRole = ref<string | ''>('')  // 角色筛选：''=全部 / admin=管理员 / student=学生
const filterStatus = ref<number | ''>('') // 状态筛选：''=全部 / 1=启用 / 0=禁用

// —— 列表数据 ——
const loading = ref(false)
const list = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)

// —— 详情弹窗状态 ——
const dialogVisible = ref(false)
const detailLoading = ref(false)
const detail = ref<any>(null)

// 角色 → { 文本, el-tag 颜色 }：管理员蓝、学生绿
function roleMeta(role: string): { text: string; type: 'primary' | 'success' } {
  if (role === 'admin') return { text: '管理员', type: 'primary' }
  return { text: '学生', type: 'success' }
}

// 状态 → { 文本, el-tag 颜色 }：启用绿、禁用红
function statusMeta(s: number): { text: string; type: 'success' | 'danger' } {
  if (s === 1) return { text: '启用', type: 'success' }
  return { text: '禁用', type: 'danger' }
}

// 时间格式化：后端返回 ISO 字符串（2026-11-05T20:31:43），转成 2026-11-05 20:31
function formatTime(t?: string): string {
  if (!t) return '-'
  return t.replace('T', ' ').slice(0, 16)
}

// 空值兜底：邮箱 / 手机号没填时显示 '-'
function showText(v?: string | null): string {
  return v && String(v).trim() !== '' ? v : '-'
}

// 拉取账号列表
async function fetchList() {
  loading.value = true
  try {
    const data: any = await request.get('/user/list', {
      params: {
        page: page.value,
        page_size: pageSize.value,
        // 角色 / 状态选「全部」时不传该参数，避免空串触发后端 422
        ...(keyword.value.trim() !== '' ? { keyword: keyword.value.trim() } : {}),
        ...(filterRole.value !== '' ? { role: filterRole.value } : {}),
        ...(filterStatus.value !== '' ? { status: filterStatus.value } : {}),
      },
    })
    list.value = data.list || []
    total.value = data.total || 0
  } catch (e) {
    // 拦截器已弹错（含学生误入被后端 403 的情况）
  } finally {
    loading.value = false
  }
}

// 查询按钮 / 回车：重置到第 1 页再查
function handleSearch() {
  page.value = 1
  fetchList()
}

// 重置：清空全部筛选条件并回到第 1 页
function handleReset() {
  keyword.value = ''
  filterRole.value = ''
  filterStatus.value = ''
  page.value = 1
  fetchList()
}

// 分页：切页 / 改每页条数
function handleCurrentChange(p: number) {
  page.value = p
  fetchList()
}
function handleSizeChange(s: number) {
  pageSize.value = s
  page.value = 1
  fetchList()
}

// 点「查看」：调详情接口，弹只读对话框（后端绝不返回 password 字段）
async function openDetail(row: any) {
  dialogVisible.value = true
  detailLoading.value = true
  detail.value = null
  try {
    const data: any = await request.get(`/user/detail/${row.id}`)
    detail.value = data
  } catch (e) {
    // 拦截器已弹错
  } finally {
    detailLoading.value = false
  }
}

// 详情头像兜底：没头像时显示姓名首字的圆形色块
function avatarInitial(): string {
  const d = detail.value
  if (!d) return '?'
  return (d.name || d.username || '?').charAt(0)
}

// 挂载：进页面就拉第一页
onMounted(() => {
  fetchList()
})
</script>

<template>
  <div class="page">
    <!-- 工具栏：关键字 + 角色筛选 + 状态筛选 + 查询 + 重置 -->
    <div class="toolbar">
      <el-input
        v-model="keyword"
        placeholder="搜索账号/姓名"
        clearable
        style="width: 200px"
        @keyup.enter="handleSearch"
        @clear="handleSearch"
      />
      <el-select v-model="filterRole" placeholder="角色" style="width: 140px" @change="handleSearch">
        <el-option label="全部角色" :value="''" />
        <el-option label="管理员" value="admin" />
        <el-option label="学生" value="student" />
      </el-select>
      <el-select v-model="filterStatus" placeholder="状态" style="width: 120px" @change="handleSearch">
        <el-option label="全部状态" :value="''" />
        <el-option label="启用" :value="1" />
        <el-option label="禁用" :value="0" />
      </el-select>
      <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
      <el-button :icon="RefreshLeft" @click="handleReset">重置</el-button>
    </div>

    <!-- 账号表格：账号/姓名/角色/邮箱/手机号/状态/创建时间/操作 -->
    <el-table :data="list" v-loading="loading" border stripe empty-text="暂无数据">
      <el-table-column prop="username" label="账号" min-width="110" show-overflow-tooltip />
      <el-table-column prop="name" label="姓名" min-width="110" show-overflow-tooltip />
      <el-table-column label="角色" width="90" align="center">
        <template #default="{ row }">
          <el-tag :type="roleMeta(row.role).type" effect="light">
            {{ roleMeta(row.role).text }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="邮箱" min-width="170" show-overflow-tooltip>
        <template #default="{ row }">{{ showText(row.email) }}</template>
      </el-table-column>
      <el-table-column label="手机号" min-width="120" show-overflow-tooltip>
        <template #default="{ row }">{{ showText(row.phone) }}</template>
      </el-table-column>
      <el-table-column label="状态" width="90" align="center">
        <template #default="{ row }">
          <el-tag :type="statusMeta(row.status).type" effect="light">
            {{ statusMeta(row.status).text }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="创建时间" width="170" align="center">
        <template #default="{ row }">{{ formatTime(row.create_time) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="80" align="center" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openDetail(row)">查看</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页：total 一项就是「共 X 条」 -->
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

    <!-- 账号详情弹窗：只读展示，绝不含密码 -->
    <el-dialog v-model="dialogVisible" title="账号详情" width="480px">
      <div v-loading="detailLoading" class="detail-box">
        <template v-if="detail">
          <!-- 头像：有图显示图片，没图用姓名首字色块兜底 -->
          <div class="detail-avatar-wrap">
            <img v-if="detail.avatar" :src="detail.avatar" class="detail-avatar" alt="头像" />
            <span v-else class="detail-avatar default-avatar">{{ avatarInitial() }}</span>
          </div>
          <el-descriptions :column="1" border size="default">
            <el-descriptions-item label="账号">{{ detail.username }}</el-descriptions-item>
            <el-descriptions-item label="姓名">{{ detail.name }}</el-descriptions-item>
            <el-descriptions-item label="角色">
              <el-tag :type="roleMeta(detail.role).type" effect="light">
                {{ roleMeta(detail.role).text }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="邮箱">{{ showText(detail.email) }}</el-descriptions-item>
            <el-descriptions-item label="手机号">{{ showText(detail.phone) }}</el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag :type="statusMeta(detail.status).type" effect="light">
                {{ statusMeta(detail.status).text }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="创建时间">{{ formatTime(detail.create_time) }}</el-descriptions-item>
          </el-descriptions>
        </template>
        <!-- 接口失败时给一行占位提示，避免空白弹窗 -->
        <p v-else-if="!detailLoading" class="detail-empty">未获取到账号信息</p>
      </div>
      <template #footer>
        <el-button @click="dialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
/* 页面卡片：与实验室/设备页同一套配色与圆角 */
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
/* 详情弹窗：头像居中 + 信息表占满宽度 */
.detail-box {
  min-height: 120px;
}
.detail-avatar-wrap {
  display: flex;
  justify-content: center;
  margin-bottom: 16px;
}
.detail-avatar {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  object-fit: cover;
  background: #eef2f8;
}
.detail-avatar.default-avatar {
  display: grid;
  place-items: center;
  color: #fff;
  font-size: 22px;
  font-weight: 600;
  background: linear-gradient(135deg, #6f9bff, #2b6cf6);
}
.detail-empty {
  text-align: center;
  color: var(--text-3, #8a94a6);
  padding: 24px 0;
}
</style>
