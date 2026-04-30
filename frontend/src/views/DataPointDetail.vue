<template>
  <div class="point-detail">
    <!-- Header Card -->
    <el-card shadow="hover" class="detail-header">
      <div class="header-row">
        <div class="header-info">
          <h2 class="point-name">{{ point.name || '数据点详情' }}</h2>
          <div class="point-meta">
            <el-tag :type="tagType(point.status)" size="small">{{ statusText(point.status) }}</el-tag>
            <span>设备: {{ point.deviceName || '--' }}</span>
            <span>层级: {{ point.hierarchyName || '--' }}</span>
          </div>
        </div>
        <div class="header-value">
          <div class="current-value" :class="`status-${point.status}`">
            {{ point.value ?? '--' }}
            <span class="unit">{{ point.unit }}</span>
          </div>
          <div class="threshold-info">阈值: {{ point.thresholdLow ?? '--' }} ~ {{ point.thresholdHigh ?? '--' }} {{ point.unit }}</div>
        </div>
      </div>
    </el-card>

    <el-row :gutter="20" style="margin-top: 20px">
      <!-- Trend Chart -->
      <el-col :xs="24" :lg="16">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>数据趋势</span>
              <div class="chart-controls">
                <el-radio-group v-model="timeRange" size="small" @change="loadHistory">
                  <el-radio-button label="1h">1小时</el-radio-button>
                  <el-radio-button label="6h">6小时</el-radio-button>
                  <el-radio-button label="24h">24小时</el-radio-button>
                  <el-radio-button label="7d">7天</el-radio-button>
                </el-radio-group>
              </div>
            </div>
          </template>
          <div ref="trendChartRef" class="trend-chart"></div>
        </el-card>
      </el-col>

      <!-- Point Info -->
      <el-col :xs="24" :lg="8">
        <el-card shadow="hover" class="info-card">
          <template #header><span>基本信息</span></template>
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="数据点名称">{{ point.name }}</el-descriptions-item>
            <el-descriptions-item label="标识符">{{ point.identifier || '--' }}</el-descriptions-item>
            <el-descriptions-item label="数据类型">{{ point.dataType || '--' }}</el-descriptions-item>
            <el-descriptions-item label="单位">{{ point.unit || '--' }}</el-descriptions-item>
            <el-descriptions-item label="所属设备">{{ point.deviceName || '--' }}</el-descriptions-item>
            <el-descriptions-item label="所属层级">{{ point.hierarchyName || '--' }}</el-descriptions-item>
            <el-descriptions-item label="采集频率">{{ point采集频率 || '--' }}秒</el-descriptions-item>
            <el-descriptions-item label="告警下限">{{ point.thresholdLow ?? '--' }}</el-descriptions-item>
            <el-descriptions-item label="告警上限">{{ point.thresholdHigh ?? '--' }}</el-descriptions-item>
            <el-descriptions-item label="最后更新">{{ formatTime(point.updatedAt) }}</el-descriptions-item>
          </el-descriptions>
        </el-card>

        <!-- Recent Alarms -->
        <el-card shadow="hover" style="margin-top: 20px">
          <template #header>
            <div class="card-header">
              <span>关联告警</span>
              <el-button type="primary" link @click="$router.push('/alarms')">查看全部</el-button>
            </div>
          </template>
          <div v-if="pointAlarms.length === 0" class="empty-alarms">
            <el-icon :size="32" color="#c0c4cc"><CircleCheck /></el-icon>
            <p>暂无告警记录</p>
          </div>
          <div v-else class="alarm-timeline">
            <div v-for="alarm in pointAlarms" :key="alarm.id" class="alarm-timeline-item">
              <div class="timeline-dot" :class="`level-${alarm.level}`"></div>
              <div class="timeline-content">
                <div class="timeline-message">{{ alarm.message }}</div>
                <div class="timeline-time">{{ formatTime(alarm.createdAt) }}</div>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import * as echarts from 'echarts'
import { getDataPointDetail } from '../api/dataPoints.js'
import { queryHistory } from '../api/history.js'
import { getAlarmList } from '../api/alarms.js'
import { getRealtimePointData } from '../api/realtime.js'
import { WebSocketManager } from '../utils/websocket.js'

const route = useRoute()
const pointId = route.params.id

const point = ref({})
const timeRange = ref('1h')
const pointAlarms = ref([])
const trendChartRef = ref(null)
let trendChart = null
let wsManager = null

function tagType(status) {
  const map = { normal: 'success', warning: 'warning', alarm: 'danger', offline: 'info' }
  return map[status] || 'info'
}

function statusText(status) {
  const map = { normal: '正常', warning: '预警', alarm: '告警', offline: '离线' }
  return map[status] || '未知'
}

function formatTime(t) {
  if (!t) return '-'
  return new Date(t).toLocaleString('zh-CN', { hour12: false })
}

async function loadPointInfo() {
  try {
    const res = await getDataPointDetail(pointId)
    point.value = res.data || {}
  } catch (e) {
    point.value = {
      id: pointId, name: 'CH₄浓度-1号井', deviceName: '甲烷传感器A', hierarchyName: '一号矿区',
      value: 0.25, unit: '%LEL', status: 'normal', thresholdLow: 0, thresholdHigh: 25,
      identifier: 'ch4_concentration', dataType: 'float', 采集频率: 10,
      updatedAt: new Date().toISOString()
    }
  }

  try {
    const rtRes = await getRealtimePointData(pointId)
    if (rtRes.data) {
      point.value = { ...point.value, ...rtRes.data }
    }
  } catch (e) { /* ignore */ }
}

async function loadHistory() {
  const rangeMs = { '1h': 3600000, '6h': 21600000, '24h': 86400000, '7d': 604800000 }
  const ms = rangeMs[timeRange.value] || 3600000
  const now = Date.now()

  let historyData = []
  try {
    const res = await queryHistory({
      pointId,
      startTime: new Date(now - ms).toISOString(),
      endTime: new Date(now).toISOString(),
      interval: timeRange.value === '7d' ? '1h' : timeRange.value === '24h' ? '15m' : '1m'
    })
    historyData = res.data || []
  } catch (e) {
    // Generate demo data
    const count = timeRange.value === '1h' ? 60 : timeRange.value === '6h' ? 72 : timeRange.value === '24h' ? 96 : 168
    const step = ms / count
    historyData = Array.from({ length: count }, (_, i) => ({
      time: new Date(now - ms + i * step).toISOString(),
      value: Math.round((20 + Math.random() * 10 + Math.sin(i / 10) * 5) * 100) / 100
    }))
  }

  updateTrendChart(historyData)
}

function updateTrendChart(data) {
  if (!trendChart) return

  const times = data.map(d => {
    const dt = new Date(d.time)
    return `${String(dt.getHours()).padStart(2, '0')}:${String(dt.getMinutes()).padStart(2, '0')}`
  })
  const values = data.map(d => d.value)

  trendChart.setOption({
    tooltip: { trigger: 'axis', formatter: '{b}<br/>值: {c} ' + (point.value?.unit || '') },
    grid: { left: 50, right: 20, top: 20, bottom: 30 },
    xAxis: { type: 'category', data: times, boundaryGap: false },
    yAxis: { type: 'value', name: point.value?.unit || '' },
    series: [{
      type: 'line',
      data: values,
      smooth: true,
      lineStyle: { width: 2, color: '#409eff' },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(64, 158, 255, 0.3)' },
          { offset: 1, color: 'rgba(64, 158, 255, 0.02)' }
        ])
      },
      itemStyle: { color: '#409eff' },
      markLine: {
        silent: true,
        data: [
          point.value?.thresholdHigh ? { yAxis: point.value.thresholdHigh, lineStyle: { color: '#f56c6c', type: 'dashed' }, label: { formatter: '上限', color: '#f56c6c' } } : null,
          point.value?.thresholdLow ? { yAxis: point.value.thresholdLow, lineStyle: { color: '#e6a23c', type: 'dashed' }, label: { formatter: '下限', color: '#e6a23c' } } : null
        ].filter(Boolean)
      }
    }]
  })
}

async function loadAlarms() {
  try {
    const res = await getAlarmList({ pointId, page: 1, pageSize: 5 })
    pointAlarms.value = res.data?.list || res.data || []
  } catch (e) {
    pointAlarms.value = [
      { id: 1, message: '浓度超过预警阈值', level: 'high', createdAt: new Date(Date.now() - 3600000).toISOString() },
      { id: 2, message: '传感器信号不稳定', level: 'medium', createdAt: new Date(Date.now() - 7200000).toISOString() }
    ]
  }
}

onMounted(async () => {
  await loadPointInfo()
  await nextTick()

  if (trendChartRef.value) {
    trendChart = echarts.init(trendChartRef.value)
    window.addEventListener('resize', () => trendChart?.resize())
  }

  loadHistory()
  loadAlarms()

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  wsManager = new WebSocketManager(`${protocol}//${window.location.host}/ws/realtime`, {
    onMessage(data) {
      if (data.type === 'data_update' && String(data.pointId) === String(pointId)) {
        point.value = { ...point.value, value: data.value, status: data.status, updatedAt: new Date().toISOString() }
      }
    }
  })
  wsManager.connect()
})

onBeforeUnmount(() => {
  trendChart?.dispose()
  wsManager?.close()
})
</script>

<style scoped>
.point-detail {
  min-height: 100%;
}

.detail-header {
  margin-bottom: 0;
}

.header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 20px;
}

.point-name {
  font-size: 20px;
  font-weight: 700;
  color: #303133;
  margin: 0 0 8px;
}

.point-meta {
  display: flex;
  align-items: center;
  gap: 16px;
  font-size: 14px;
  color: #909399;
}

.current-value {
  font-size: 42px;
  font-weight: 700;
  font-family: 'DIN', 'Helvetica Neue', monospace;
  text-align: right;
  line-height: 1;
}

.current-value .unit {
  font-size: 16px;
  color: #909399;
  font-weight: 400;
}

.current-value.status-normal { color: #67c23a; }
.current-value.status-warning { color: #e6a23c; }
.current-value.status-alarm { color: #f56c6c; }
.current-value.status-offline { color: #c0c4cc; }

.threshold-info {
  font-size: 13px;
  color: #909399;
  text-align: right;
  margin-top: 4px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.trend-chart {
  height: 350px;
}

.info-card :deep(.el-descriptions) {
  margin-top: 0;
}

.empty-alarms {
  text-align: center;
  padding: 24px 0;
  color: #c0c4cc;
}

.empty-alarms p {
  margin-top: 8px;
  font-size: 13px;
}

.alarm-timeline {
  max-height: 300px;
  overflow-y: auto;
}

.alarm-timeline-item {
  display: flex;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid #f0f0f0;
}

.alarm-timeline-item:last-child {
  border-bottom: none;
}

.timeline-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-top: 6px;
  flex-shrink: 0;
}

.timeline-dot.level-critical { background: #f56c6c; }
.timeline-dot.level-high { background: #e6a23c; }
.timeline-dot.level-medium { background: #409eff; }
.timeline-dot.level-low { background: #909399; }

.timeline-message {
  font-size: 13px;
  color: #303133;
  margin-bottom: 2px;
}

.timeline-time {
  font-size: 12px;
  color: #c0c4cc;
}
</style>
