<script setup lang="ts">
// 引入 Element Plus 提示与二次确认弹窗
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
// 统一请求工具
import request from '@/utils/request'

// —— 筛选条件：状态筛选（''=全部 / 0=待审核 / 1=已通过 / 2=已拒绝 / 3=已取消 / 4=已结束）——
const filterStatus = ref<number | ''>('')

// —— 列表数据状态 ——
const loading = ref(false)
const list = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)

// 局部函数：预约状态数字 → { 文本, el-tag 类型 }
function appointmentStatusMeta(s: number): {
  text: string
  type: 'success' | 'warning' | 'danger' | 'info'
} {
  if (s === 0) return { text: '待审核', type: 'warning' }
  if (s === 1) return { text: '已通过', type: 'success' }
  if (s === 2) return { text: '已拒绝', type: 'danger' }
  if (s === 3) return { text: '已取消', type: 'info' }
  // 4=已结束：结束时间过期后由后端定时任务自动置为此状态
  return { text: '已结束', type: 'info' }
}

// 把 "HH:mm:ss" 截取前 5 位 "HH:mm" 用 ~ 连接成时间段
function timeRange(start: string, end: string): string {
  const s = (start || '').slice(0, 5)
  const e = (end || '').slice(0, 5)
  return `${s} ~ ${e}`
}

// 拉取「我的预约」列表
async function fetchList() {
  loading.value = true
  try {
    const data: any = await request.get('/appointment/my', {
      params: {
        page: page.value,
        page_size: pageSize.value,
        // 状态为空（全部）时不传，避免把空串发给后端导致 422
        ...(filterStatus.value !== '' ? { status: filterStatus.value } : {}),
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

// 筛选变化：回到第一页
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

// 取消预约：二次确认后 PUT /appointment/{id}/cancel
async function handleCancel(row: any) {
  try {
    await ElMessageBox.confirm(
      '确定要取消该预约吗？',
      '取消确认',
      { type: 'warning', confirmButtonText: '确定取消', cancelButtonText: '取消' },
    )
  } catch (e) {
    // 用户点取消，直接返回
    return
  }
  try {
    await request.put(`/appointment/${row.id}/cancel`)
    ElMessage.success('已取消预约')
    fetchList()
  } catch (e) {
    // 拦截器已弹错（仅本人且 status 为 0/1 可取消，否则后端 400）
  }
}

// 挂载即拉取
onMounted(() => {
  fetchList()
})
</script>

<template>
  <div class="page">
    <!-- 工具栏：状态筛选 -->
    <div class="toolbar">
      <el-select
        v-model="filterStatus"
        placeholder="状态"
        clearable
        style="width: 160px"
        @change="handleSearch"
      >
        <el-option label="全部" :value="''" />
        <el-option label="待审核" :value="0" />
        <el-option label="已通过" :value="1" />
        <el-option label="已拒绝" :value="2" />
        <el-option label="已取消" :value="3" />
        <el-option label="已结束" :value="4" />
      </el-select>
    </div>

    <!-- 我的预约表格 -->
    <el-table :data="list" v-loading="loading" border stripe>
      <el-table-column prop="lab_name" label="实验室" min-width="130" />
      <el-table-column prop="device_name" label="设备" min-width="120">
        <template #default="{ row }">
          {{ row.device_name || '不指定' }}
        </template>
      </el-table-column>
      <el-table-column prop="appoint_date" label="日期" width="120" />
      <el-table-column label="时间段" width="140">
        <template #default="{ row }">
          {{ timeRange(row.start_time, row.end_time) }}
        </template>
      </el-table-column>
      <el-table-column prop="purpose" label="用途" min-width="160" show-overflow-tooltip />
      <el-table-column label="状态" width="100" align="center">
        <template #default="{ row }">
          <el-tag :type="appointmentStatusMeta(row.status).type" effect="light">
            {{ appointmentStatusMeta(row.status).text }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="120" align="center" fixed="right">
        <template #default="{ row }">
          <!-- 仅待审核(0)或已通过(1)可取消 -->
          <el-button
            v-if="row.status === 0 || row.status === 1"
            link
            type="danger"
            @click="handleCancel(row)"
          >
            取消
          </el-button>
          <span v-else class="muted">—</span>
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
.muted {
  color: var(--text-3);
}
</style>
