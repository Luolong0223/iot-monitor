<template>
  <div class="operation-logs">
    <h2>操作日志</h2>

    <el-card shadow="never" class="filter-card">
      <el-form :inline="true" :model="filter">
        <el-form-item label="用户名">
          <el-input v-model="filter.username" placeholder="用户名" clearable />
        </el-form-item>
        <el-form-item label="模块">
          <el-select v-model="filter.module" clearable placeholder="全部">
            <el-option v-for="m in modules" :key="m" :label="m" :value="m" />
          </el-select>
        </el-form-item>
        <el-form-item label="操作类型">
          <el-select v-model="filter.action" clearable placeholder="全部">
            <el-option v-for="a in actions" :key="a" :label="a" :value="a" />
          </el-select>
        </el-form-item>
        <el-form-item label="时间范围">
          <el-date-picker v-model="dateRange" type="datetimerange" range-separator="至"
            start-placeholder="开始" end-placeholder="结束" value-format="YYYY-MM-DD HH:mm:ss"
            @change="onDateChange" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadData">查询</el-button>
          <el-button @click="resetFilter">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never">
      <el-table :data="logs" v-loading="loading" stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="created_at" label="时间" width="170" />
        <el-table-column prop="username" label="用户" width="100" />
        <el-table-column prop="action" label="操作" width="90">
          <template #default="{ row }">
            <el-tag :type="actionTagType(row.action)" size="small">{{ row.action }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="module" label="模块" width="100" />
        <el-table-column prop="target_desc" label="操作对象" width="180" />
        <el-table-column prop="ip_address" label="IP地址" width="130" />
        <el-table-column label="详情" min-width="120">
          <template #default="{ row }">
            <el-button v-if="row.detail" size="small" link @click="showDetail(row)">查看</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="filter.page"
          v-model:page-size="filter.page_size"
          :total="total"
          :page-sizes="[20, 50, 100]"
          layout="total, sizes, prev, pager, next"
          @current-change="loadData"
          @size-change="loadData"
        />
      </div>
    </el-card>

    <!-- 详情弹窗 -->
    <el-dialog v-model="detailVisible" title="操作详情" width="600px">
      <pre class="detail-pre">{{ detailJson }}</pre>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { getOperationLogs } from '@/api/system'

const loading = ref(false)
const logs = ref([])
const total = ref(0)
const dateRange = ref(null)
const detailVisible = ref(false)
const detailJson = ref('')

const modules = ['hierarchy', 'device', 'point', 'protocol', 'user', 'alarm', 'system']
const actions = ['login', 'logout', 'create', 'update', 'delete', 'export']

const filter = reactive({ username: '', module: '', action: '', start_time: '', end_time: '', page: 1, page_size: 20 })

const onDateChange = (val) => {
  filter.start_time = val ? val[0] : ''
  filter.end_time = val ? val[1] : ''
}

const actionTagType = (a) => ({ login: 'success', logout: 'info', create: '', update: 'warning', delete: 'danger', export: '' }[a] || '')

const loadData = async () => {
  loading.value = true
  try {
    const res = await getOperationLogs(filter)
    logs.value = res.data.data.list
    total.value = res.data.data.total
  } finally { loading.value = false }
}

const resetFilter = () => {
  Object.assign(filter, { username: '', module: '', action: '', start_time: '', end_time: '', page: 1, page_size: 20 })
  dateRange.value = null
  loadData()
}

const showDetail = (row) => {
  detailJson.value = JSON.stringify(row.detail, null, 2)
  detailVisible.value = true
}

onMounted(loadData)
</script>

<style scoped>
.filter-card { margin-bottom: 16px; }
.pagination-wrap { display: flex; justify-content: flex-end; margin-top: 16px; }
.detail-pre { background: #f5f7fa; padding: 12px; border-radius: 4px; font-size: 13px; overflow-x: auto; white-space: pre-wrap; }
</style>
