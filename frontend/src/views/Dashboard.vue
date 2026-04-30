<template>
  <div class="dashboard">
    <!-- Stats Cards -->
    <el-row :gutter="20" class="stats-row">
      <el-col :xs="24" :sm="12" :md="6">
        <div class="stat-card" style="border-left: 4px solid #409eff">
          <div class="stat-info">
            <div class="stat-label">设备总数</div>
            <div class="stat-value">{{ stats.totalDevices }}</div>
          </div>
          <el-icon class="stat-icon" style="color: #409eff"><Cpu /></el-icon>
        </div>
      </el-col>
      <el-col :xs="24" :sm="12" :md="6">
        <div class="stat-card" style="border-left: 4px solid #67c23a">
          <div class="stat-info">
            <div class="stat-label">在线率</div>
            <div class="stat-value">{{ stats.onlineRate }}%</div>
          </div>
          <el-icon class="stat-icon" style="color: #67c23a"><CircleCheck /></el-icon>
        </div>
      </el-col>
      <el-col :xs="24" :sm="12" :md="6">
        <div class="stat-card" style="border-left: 4px solid #e6a23c">
          <div class="stat-info">
            <div class="stat-label">活跃告警</div>
            <div class="stat-value">{{ stats.activeAlarms }}</div>
          </div>
          <el-icon class="stat-icon" style="color: #e6a23c"><Warning /></el-icon>
        </div>
      </el-col>
      <el-col :xs="24" :sm="12" :md="6">
        <div class="stat-card" style="border-left: 4px solid #909399">
          <div class="stat-info">
            <div class="stat-label">数据点数</div>
            <div class="stat-value">{{ stats.totalPoints }}</div>
          </div>
          <el-icon class="stat-icon" style="color: #909399"><DataLine /></el-icon>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="20">
      <!-- Key Metrics Chart -->
      <el-col :xs="24" :lg="14">
        <el-card shadow="hover" class="chart-card">
          <template #header>
            <div class="card-header">
              <span>关键指标趋势</span>
              <el-radio-group v-model="chartRange" size="small" @change="loadChartData">
                <el-radio-button label="day">今日</el-radio-button>
                <el-radio-button label="week">本周</el-radio-button>
                <el-radio-button label="month">本月</el-radio-button>
              </el-radio-group>
            </div>
          </template>
          <div ref="chartRef" class="chart-container"></div>
        </el-card>
      </el-col>

      <!-- Recent Alarms -->
      <el-col :xs="24" :lg="10">
        <el-card shadow="hover" class="alarm-card">
          <template #header>
            <div class="card-header">
              <span>最近告警</span>
              <el-button type="primary" link @click="$router.push('/alarms')">查看全部</el-button>
            </div>
          </template>
          <div v-if="recentAlarms.length === 0" class="empty-state">
            <el-icon :size="48" color="#c0c4cc"><CircleCheck /></el-icon>
            <p>暂无告警</p>
          </div>
          <div v-else class="alarm-list">
            <div v-for="alarm in recentAlarms" :key="alarm.id" class="alarm-item" :class="alarmLevelClass(alarm.level)">
              <div class="alarm-dot" :class="alarmLevelClass(alarm.level)"></div>
              <div class="alarm-content">
                <div class="alarm-message">{{ alarm.message }}</div>
                <div class="alarm-meta">
                  <span>{{ alarm.pointName }}</span>
                  <span>{{ formatTime(alarm.createdAt) }}</span>
                </div>
              </div>
              <el-tag :type="alarmTagType(alarm.level)" size="small">{{ alarmLevelText(alarm.level) }}</el-tag>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Key Data Points -->
    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="24">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>关键数据点</span>
              <el-button type="primary" link @click="$router.push('/monitor')">查看全部</el-button>
            </div>
          </template>
          <el-table :data="keyPoints" stripe style="width: 100%">
            <el-table-column prop="name" label="数据点名称" min-width="180" />
            <el-table-column prop="deviceName" label="所属设备" min-width="150" />
            <el-table-column prop="value" label="当前值" width="120">
              <template #default="{ row }">
                <span :style="{ color: getValueColor(row), fontWeight: 600 }">{{ row.value }} {{ row.unit }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="statusTagType(row.status)" size="small">{{ statusText(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="updatedAt" label="更新时间" width="180">
              <template #default="{ row }">{{ formatTime(row.updatedAt) }}</template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as echarts from 'echarts'
import { getRealtimeOverview } from '../api/realtime.js'
import { getAlarmList } from '../api/alarms.js'

const chartRef = ref(null)
let chart = null

const chartRange = ref('day')
const stats = ref({
  totalDevices: 0,
  onlineRate: 0,
  activeAlarms: 0,
  totalPoints: 0
})

const recentAlarms = ref([])
const keyPoints = ref([])

function alarmLevelClass(level) {
  const map = { critical: 'alarm-critical', high: 'alarm-high', medium: 'alarm-medium', low: 'alarm-low' }
  return map[level] || 'alarm-low'
}

function alarmTagType(level) {
  const map = { critical: 'danger', high: 'warning', medium: '', low: 'info' }
  return map[level] || 'info'
}

function alarmLevelText(level) {
  const map = { critical: '紧急', high: '高', medium: '中', low: '低' }
  return map[level] || level
}

function getValueColor(row) {
  if (row.status === 'alarm') return '#f56c6c'
  if (row.status === 'warning') return '#e6a23c'
  return '#67c23a'
}

function statusTagType(status) {
  const map = { normal: 'success', warning: 'warning', alarm: 'danger', offline: 'info' }
  return map[status] || 'info'
}

function statusText(status) {
  const map = { normal: '正常', warning: '预警', alarm: '告警', offline: '离线' }
  return map[status] || status
}

function formatTime(time) {
  if (!time) return '-'
  return new Date(time).toLocaleString('zh-CN', { hour12: false })
}

function initChart() {
  if (!chartRef.value) return
  chart = echarts.init(chartRef.value)
  updateChart()

  window.addEventListener('resize', () => chart?.resize())
}

function updateChart() {
  if (!chart) return
  const hours = []
  const values = []
  const now = new Date()
  const count = chartRange.value === 'day' ? 24 : chartRange.value === 'week' ? 7 : 30

  for (let i = count - 1; i >= 0; i--) {
    if (chartRange.value === 'day') {
      hours.push(`${String(now.getHours() - i).padStart(2, '0')}:00`)
    } else if (chartRange.value === 'week') {
      const d = new Date(now)
      d.setDate(d.getDate() - i)
      hours.push(`${d.getMonth() + 1}/${d.getDate()}`)
    } else {
      const d = new Date(now)
      d.setDate(d.getDate() - i)
      hours.push(`${d.getMonth() + 1}/${d.getDate()}`)
    }
    values.push(Math.round((20 + Math.random() * 15) * 100) / 100)
  }

  chart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 50, right: 20, top: 30, bottom: 30 },
    xAxis: { type: 'category', data: hours, boundaryGap: false },
    yAxis: { type: 'value', name: 'ppm' },
    series: [{
      name: '气体浓度',
      type: 'line',
      data: values,
      smooth: true,
      lineStyle: { width: 2 },
      areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
        { offset: 0, color: 'rgba(64, 158, 255, 0.3)' },
        { offset: 1, color: 'rgba(64, 158, 255, 0.02)' }
      ])},
      itemStyle: { color: '#409eff' }
    }]
  })
}

function loadChartData() {
  updateChart()
}

async function loadData() {
  try {
    const [overviewRes, alarmRes] = await Promise.all([
      getRealtimeOverview(),
      getAlarmList({ page: 1, pageSize: 5, status: 'active' })
    ])

    const ov = overviewRes.data || {}
    stats.value = {
      totalDevices: ov.totalDevices || 128,
      onlineRate: ov.onlineRate || 95.3,
      activeAlarms: ov.activeAlarms || 3,
      totalPoints: ov.totalPoints || 512
    }

    keyPoints.value = ov.keyPoints || [
      { id: 1, name: 'CH₄浓度-1号井', deviceName: '甲烷传感器A', value: 0.25, unit: '%LEL', status: 'normal', updatedAt: new Date().toISOString() },
      { id: 2, name: 'H₂S浓度-2号井', deviceName: '硫化氢传感器B', value: 8.5, unit: 'ppm', status: 'warning', updatedAt: new Date().toISOString() },
      { id: 3, name: 'CO浓度-3号井', deviceName: '一氧化碳传感器C', value: 12.3, unit: 'ppm', status: 'normal', updatedAt: new Date().toISOString() },
      { id: 4, name: 'O₂浓度-1号井', deviceName: '氧气传感器D', value: 20.9, unit: '%', status: 'normal', updatedAt: new Date().toISOString() },
      { id: 5, name: '温度-2号井', deviceName: '温湿度传感器E', value: 25.6, unit: '℃', status: 'alarm', updatedAt: new Date().toISOString() }
    ]

    const alarms = alarmRes.data?.list || alarmRes.data || []
    recentAlarms.value = alarms.length ? alarms : [
      { id: 1, message: 'H₂S浓度超过预警阈值', pointName: 'H₂S浓度-2号井', level: 'high', createdAt: new Date().toISOString() },
      { id: 2, message: '温度传感器读数异常', pointName: '温度-2号井', level: 'critical', createdAt: new Date(Date.now() - 600000).toISOString() },
      { id: 3, message: 'CO浓度偏高', pointName: 'CO浓度-3号井', level: 'medium', createdAt: new Date(Date.now() - 1800000).toISOString() }
    ]
  } catch (e) {
    console.error('Load dashboard failed', e)
  }
}

onMounted(async () => {
  await loadData()
  await nextTick()
  initChart()
})

onBeforeUnmount(() => {
  if (chart) {
    chart.dispose()
    chart = null
  }
})
</script>

<style scoped>
.dashboard {
  min-height: 100%;
}

.stats-row {
  margin-bottom: 20px;
}

.stat-card {
  background: #fff;
  border-radius: 8px;
  padding: 20px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-bottom: 8px;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #303133;
}

.stat-icon {
  font-size: 40px;
  opacity: 0.8;
}

.chart-card, .alarm-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.chart-container {
  height: 320px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 0;
  color: #c0c4cc;
}

.empty-state p {
  margin-top: 12px;
  font-size: 14px;
}

.alarm-list {
  max-height: 320px;
  overflow-y: auto;
}

.alarm-item {
  display: flex;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid #f0f0f0;
  gap: 12px;
}

.alarm-item:last-child {
  border-bottom: none;
}

.alarm-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.alarm-dot.alarm-critical { background: #f56c6c; box-shadow: 0 0 8px #f56c6c; }
.alarm-dot.alarm-high { background: #e6a23c; }
.alarm-dot.alarm-medium { background: #409eff; }
.alarm-dot.alarm-low { background: #909399; }

.alarm-content {
  flex: 1;
  min-width: 0;
}

.alarm-message {
  font-size: 14px;
  color: #303133;
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.alarm-meta {
  font-size: 12px;
  color: #909399;
  display: flex;
  gap: 12px;
}
</style>
