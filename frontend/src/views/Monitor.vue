<template>
  <div class="monitor-page">
    <div class="monitor-toolbar">
      <el-input v-model="searchText" placeholder="搜索数据点..." prefix-icon="Search" clearable style="width: 300px" />
      <el-select v-model="statusFilter" placeholder="状态筛选" clearable style="width: 140px">
        <el-option label="全部" value="" />
        <el-option label="正常" value="normal" />
        <el-option label="预警" value="warning" />
        <el-option label="告警" value="alarm" />
        <el-option label="离线" value="offline" />
      </el-select>
      <el-select v-model="viewMode" style="width: 120px">
        <el-option label="卡片视图" value="card" />
        <el-option label="表格视图" value="table" />
      </el-select>
      <div class="toolbar-right">
        <span class="update-time">最后更新: {{ lastUpdate }}</span>
        <el-button :icon="Refresh" circle @click="loadData" />
      </div>
    </div>

    <!-- Card View -->
    <div v-if="viewMode === 'card'" class="monitor-grid">
      <div
        v-for="point in filteredPoints"
        :key="point.id"
        class="monitor-card"
        :class="statusClass(point.status)"
        @click="goToDetail(point)"
      >
        <div class="card-header-row">
          <span class="point-name">{{ point.name }}</span>
          <span class="status-badge" :class="statusClass(point.status)">{{ statusText(point.status) }}</span>
        </div>
        <div class="card-value">
          <span class="value" :class="statusClass(point.status)">{{ point.value ?? '--' }}</span>
          <span class="unit">{{ point.unit }}</span>
        </div>
        <div class="card-meta">
          <span>{{ point.deviceName }}</span>
          <span>{{ point.hierarchyName }}</span>
        </div>
        <div class="card-footer">
          <span class="threshold">阈值: {{ point.thresholdLow ?? '--' }} ~ {{ point.thresholdHigh ?? '--' }} {{ point.unit }}</span>
          <span class="time">{{ formatTimeShort(point.updatedAt) }}</span>
        </div>
        <div class="card-indicator" :class="statusClass(point.status)"></div>
      </div>
    </div>

    <!-- Table View -->
    <el-card v-else shadow="hover">
      <el-table :data="filteredPoints" stripe style="width: 100%" @row-click="goToDetail">
        <el-table-column prop="name" label="数据点名称" min-width="180" />
        <el-table-column prop="deviceName" label="所属设备" min-width="150" />
        <el-table-column prop="hierarchyName" label="所属层级" min-width="120" />
        <el-table-column prop="value" label="当前值" width="120">
          <template #default="{ row }">
            <span :style="{ color: valueColor(row.status), fontWeight: 700, fontSize: '16px' }">
              {{ row.value ?? '--' }} {{ row.unit }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="tagType(row.status)" size="small">{{ statusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="thresholdLow" label="下限" width="80" />
        <el-table-column prop="thresholdHigh" label="上限" width="80" />
        <el-table-column prop="updatedAt" label="更新时间" width="180">
          <template #default="{ row }">{{ formatTime(row.updatedAt) }}</template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { Refresh } from '@element-plus/icons-vue'
import { getRealtimeAllPoints } from '../api/realtime.js'
import { WebSocketManager } from '../utils/websocket.js'

const router = useRouter()

const searchText = ref('')
const statusFilter = ref('')
const viewMode = ref('card')
const lastUpdate = ref('')
const points = ref([])

let wsManager = null
let refreshTimer = null

const filteredPoints = computed(() => {
  let list = points.value
  if (searchText.value) {
    const q = searchText.value.toLowerCase()
    list = list.filter(p => p.name.toLowerCase().includes(q) || (p.deviceName || '').toLowerCase().includes(q))
  }
  if (statusFilter.value) {
    list = list.filter(p => p.status === statusFilter.value)
  }
  return list
})

function statusClass(status) {
  return `status-${status || 'offline'}`
}

function statusText(status) {
  const map = { normal: '正常', warning: '预警', alarm: '告警', offline: '离线' }
  return map[status] || '未知'
}

function tagType(status) {
  const map = { normal: 'success', warning: 'warning', alarm: 'danger', offline: 'info' }
  return map[status] || 'info'
}

function valueColor(status) {
  const map = { normal: '#67c23a', warning: '#e6a23c', alarm: '#f56c6c', offline: '#c0c4cc' }
  return map[status] || '#909399'
}

function formatTime(t) {
  if (!t) return '-'
  return new Date(t).toLocaleString('zh-CN', { hour12: false })
}

function formatTimeShort(t) {
  if (!t) return '-'
  const d = new Date(t)
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}:${String(d.getSeconds()).padStart(2, '0')}`
}

function goToDetail(row) {
  router.push(`/data-point/${row.id}`)
}

async function loadData() {
  try {
    const res = await getRealtimeAllPoints()
    points.value = res.data || res.data?.list || []
    if (!points.value.length) {
      // Generate demo data
      points.value = generateDemoPoints()
    }
    lastUpdate.value = new Date().toLocaleString('zh-CN', { hour12: false })
  } catch (e) {
    points.value = generateDemoPoints()
    lastUpdate.value = new Date().toLocaleString('zh-CN', { hour12: false })
  }
}

function generateDemoPoints() {
  const statuses = ['normal', 'normal', 'normal', 'warning', 'alarm', 'normal', 'offline', 'normal']
  return Array.from({ length: 24 }, (_, i) => {
    const status = statuses[i % statuses.length]
    return {
      id: i + 1,
      name: ['CH₄浓度', 'H₂S浓度', 'CO浓度', 'O₂浓度', '温度', '压力', '流速', '湿度'][i % 8] + `-${Math.floor(i / 8) + 1}号井`,
      deviceName: ['甲烷传感器', '硫化氢传感器', '一氧化碳传感器', '氧气传感器', '温湿度传感器', '压力传感器', '流速传感器', '湿度传感器'][i % 8] + String.fromCharCode(65 + (i % 8)),
      hierarchyName: ['一号矿区', '二号矿区', '三号矿区'][i % 3],
      value: status === 'offline' ? null : Math.round((Math.random() * 50 + 10) * 100) / 100,
      unit: ['%LEL', 'ppm', 'ppm', '%', '℃', 'kPa', 'm/s', '%'][i % 8],
      status,
      thresholdLow: [0, 0, 0, 19.5, 15, 80, 0, 30][i % 8],
      thresholdHigh: [25, 10, 24, 23.5, 35, 120, 10, 80][i % 8],
      updatedAt: new Date(Date.now() - Math.random() * 600000).toISOString()
    }
  })
}

onMounted(() => {
  loadData()

  // Auto-refresh every 30 seconds
  refreshTimer = setInterval(loadData, 30000)

  // WebSocket for real-time updates
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  wsManager = new WebSocketManager(`${protocol}//${window.location.host}/ws/realtime`, {
    onMessage(data) {
      if (data.type === 'data_update' && data.pointId) {
        const idx = points.value.findIndex(p => p.id === data.pointId)
        if (idx !== -1) {
          points.value[idx] = { ...points.value[idx], ...data }
        }
      }
    }
  })
  wsManager.connect()
})

onBeforeUnmount(() => {
  if (refreshTimer) clearInterval(refreshTimer)
  if (wsManager) wsManager.close()
})
</script>

<style scoped>
.monitor-page {
  min-height: 100%;
}

.monitor-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.toolbar-right {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 12px;
}

.update-time {
  font-size: 13px;
  color: #909399;
}

.monitor-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.monitor-card {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.3s;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
  position: relative;
  overflow: hidden;
}

.monitor-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
}

.card-indicator {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
}

.card-indicator.status-normal { background: #67c23a; }
.card-indicator.status-warning { background: #e6a23c; }
.card-indicator.status-alarm { background: #f56c6c; animation: pulse 2s infinite; }
.card-indicator.status-offline { background: #c0c4cc; }

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.card-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.point-name {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 180px;
}

.status-badge {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 500;
}

.status-badge.status-normal { background: #f0f9eb; color: #67c23a; }
.status-badge.status-warning { background: #fdf6ec; color: #e6a23c; }
.status-badge.status-alarm { background: #fef0f0; color: #f56c6c; }
.status-badge.status-offline { background: #f4f4f5; color: #c0c4cc; }

.card-value {
  display: flex;
  align-items: baseline;
  gap: 4px;
  margin-bottom: 12px;
}

.value {
  font-size: 36px;
  font-weight: 700;
  font-family: 'DIN', 'Helvetica Neue', monospace;
  line-height: 1;
}

.value.status-normal { color: #67c23a; }
.value.status-warning { color: #e6a23c; }
.value.status-alarm { color: #f56c6c; }
.value.status-offline { color: #c0c4cc; }

.unit {
  font-size: 14px;
  color: #909399;
}

.card-meta {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #909399;
  margin-bottom: 8px;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #c0c4cc;
  padding-top: 8px;
  border-top: 1px solid #f0f0f0;
}

.threshold {
  font-size: 11px;
}

@media (max-width: 768px) {
  .monitor-grid {
    grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  }
  .value {
    font-size: 28px;
  }
}
</style>
