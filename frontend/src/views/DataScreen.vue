<template>
  <div class="data-screen" :class="{ fullscreen: isFullscreen }">
    <!-- Header -->
    <div class="screen-header">
      <div class="header-left">
        <div class="logo-area">
          <img src="https://cdn-icons-png.flaticon.com/512/2917/2917995.png" alt="logo" class="logo" />
          <span class="title">气体监测物联网平台</span>
        </div>
      </div>
      <div class="header-center">
        <span class="datetime">{{ currentTime }}</span>
      </div>
      <div class="header-right">
        <el-button class="screen-btn" :icon="FullScreen" circle @click="toggleFullscreen" />
        <el-button class="screen-btn" :icon="Back" circle @click="$router.push('/dashboard')" />
      </div>
    </div>

    <!-- Content -->
    <div class="screen-body">
      <!-- Top Stats -->
      <div class="top-stats">
        <div class="big-stat" v-for="stat in bigStats" :key="stat.label">
          <div class="big-stat-value">
            <span class="number">{{ stat.value }}</span>
            <span class="suffix">{{ stat.suffix }}</span>
          </div>
          <div class="big-stat-label">{{ stat.label }}</div>
        </div>
      </div>

      <!-- Main Content -->
      <div class="screen-main">
        <!-- Left: Alarm List -->
        <div class="screen-left">
          <div class="panel">
            <div class="panel-title">
              <span class="title-icon">⚠</span> 实时告警
            </div>
            <div class="alarm-scroll" ref="alarmScrollRef">
              <div v-for="alarm in alarms" :key="alarm.id" class="screen-alarm-item" :class="`level-${alarm.level}`">
                <span class="alarm-level-tag">{{ levelText(alarm.level) }}</span>
                <span class="alarm-text">{{ alarm.message }}</span>
                <span class="alarm-time">{{ formatTimeShort(alarm.createdAt) }}</span>
              </div>
              <div v-if="!alarms.length" class="no-data">暂无告警</div>
            </div>
          </div>
        </div>

        <!-- Center: Charts -->
        <div class="screen-center">
          <div class="panel">
            <div class="panel-title">
              <span class="title-icon">📊</span> 实时数据趋势
            </div>
            <div ref="mainChartRef" class="main-chart"></div>
          </div>
          <div class="center-bottom">
            <div class="panel half">
              <div class="panel-title">
                <span class="title-icon">🏭</span> 设备状态
              </div>
              <div ref="deviceChartRef" class="small-chart"></div>
            </div>
            <div class="panel half">
              <div class="panel-title">
                <span class="title-icon">📈</span> 告警统计
              </div>
              <div ref="alarmChartRef" class="small-chart"></div>
            </div>
          </div>
        </div>

        <!-- Right: Key Points -->
        <div class="screen-right">
          <div class="panel">
            <div class="panel-title">
              <span class="title-icon">📋</span> 关键数据点
            </div>
            <div class="key-points-list">
              <div v-for="point in keyPoints" :key="point.id" class="key-point-item" :class="`status-${point.status}`">
                <div class="kp-name">{{ point.name }}</div>
                <div class="kp-value-row">
                  <span class="kp-value">{{ point.value ?? '--' }}</span>
                  <span class="kp-unit">{{ point.unit }}</span>
                </div>
                <div class="kp-bar">
                  <div class="kp-bar-fill" :class="`status-${point.status}`" :style="{ width: barWidth(point) }"></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as echarts from 'echarts'
import { FullScreen, Back } from '@element-plus/icons-vue'
import { getRealtimeOverview } from '../api/realtime.js'
import { getAlarmList } from '../api/alarms.js'

const isFullscreen = ref(false)
const currentTime = ref('')
let timeTimer = null

const bigStats = ref([
  { label: '设备总数', value: 128, suffix: '台' },
  { label: '在线设备', value: 122, suffix: '台' },
  { label: '在线率', value: 95.3, suffix: '%' },
  { label: '活跃告警', value: 3, suffix: '条' },
  { label: '数据点数', value: 512, suffix: '个' }
])

const alarms = ref([])
const keyPoints = ref([])

const mainChartRef = ref(null)
const deviceChartRef = ref(null)
const alarmChartRef = ref(null)
const alarmScrollRef = ref(null)

let mainChart = null
let deviceChart = null
let alarmChart = null

function levelText(level) {
  const map = { critical: '紧急', high: '高', medium: '中', low: '低' }
  return map[level] || level
}

function formatTimeShort(t) {
  if (!t) return ''
  const d = new Date(t)
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

function barWidth(point) {
  if (!point.thresholdHigh || point.value == null) return '50%'
  const pct = Math.min(100, (point.value / point.thresholdHigh) * 100)
  return `${pct}%`
}

function toggleFullscreen() {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen()
    isFullscreen.value = true
  } else {
    document.exitFullscreen()
    isFullscreen.value = false
  }
}

function updateTime() {
  currentTime.value = new Date().toLocaleString('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
    hour12: false
  })
}

function initMainChart() {
  if (!mainChartRef.value) return
  mainChart = echarts.init(mainChartRef.value)

  const hours = Array.from({ length: 24 }, (_, i) => `${String(i).padStart(2, '0')}:00`)
  const series = [
    { name: 'CH₄', data: hours.map(() => (Math.random() * 20 + 5).toFixed(1)), color: '#409eff' },
    { name: 'H₂S', data: hours.map(() => (Math.random() * 8 + 1).toFixed(1)), color: '#e6a23c' },
    { name: 'CO', data: hours.map(() => (Math.random() * 15 + 3).toFixed(1)), color: '#f56c6c' },
    { name: 'O₂', data: hours.map(() => (Math.random() * 2 + 20).toFixed(1)), color: '#67c23a' }
  ]

  mainChart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: series.map(s => s.name), textStyle: { color: '#c0c4cc' }, top: 5 },
    grid: { left: 50, right: 20, top: 40, bottom: 30 },
    xAxis: { type: 'category', data: hours, axisLine: { lineStyle: { color: '#ffffff30' } }, axisLabel: { color: '#c0c4cc', fontSize: 10 } },
    yAxis: { type: 'value', axisLine: { lineStyle: { color: '#ffffff30' } }, splitLine: { lineStyle: { color: '#ffffff10' } }, axisLabel: { color: '#c0c4cc' } },
    series: series.map(s => ({
      name: s.name, type: 'line', data: s.data, smooth: true,
      lineStyle: { width: 2 }, itemStyle: { color: s.color }, showSymbol: false
    }))
  })
}

function initDeviceChart() {
  if (!deviceChartRef.value) return
  deviceChart = echarts.init(deviceChartRef.value)

  deviceChart.setOption({
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      center: ['50%', '55%'],
      data: [
        { value: 122, name: '在线', itemStyle: { color: '#67c23a' } },
        { value: 4, name: '离线', itemStyle: { color: '#909399' } },
        { value: 2, name: '故障', itemStyle: { color: '#f56c6c' } }
      ],
      label: { color: '#c0c4cc', fontSize: 11 },
      labelLine: { lineStyle: { color: '#ffffff30' } }
    }]
  })
}

function initAlarmChart() {
  if (!alarmChartRef.value) return
  alarmChart = echarts.init(alarmChartRef.value)

  alarmChart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 40, right: 10, top: 10, bottom: 25 },
    xAxis: { type: 'category', data: ['周一', '周二', '周三', '周四', '周五', '周六', '周日'], axisLine: { lineStyle: { color: '#ffffff30' } }, axisLabel: { color: '#c0c4cc', fontSize: 10 } },
    yAxis: { type: 'value', axisLine: { lineStyle: { color: '#ffffff30' } }, splitLine: { lineStyle: { color: '#ffffff10' } }, axisLabel: { color: '#c0c4cc' } },
    series: [{
      type: 'bar',
      data: [5, 3, 7, 2, 4, 1, 3],
      itemStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: '#f56c6c' },
          { offset: 1, color: '#e6a23c' }
        ]),
        borderRadius: [4, 4, 0, 0]
      }
    }]
  })
}

function handleResize() {
  mainChart?.resize()
  deviceChart?.resize()
  alarmChart?.resize()
}

async function loadData() {
  try {
    const [ovRes, alarmRes] = await Promise.all([
      getRealtimeOverview().catch(() => ({ data: null })),
      getAlarmList({ page: 1, pageSize: 20, status: 'active' }).catch(() => ({ data: { list: [] } }))
    ])

    const ov = ovRes.data || {}
    bigStats.value = [
      { label: '设备总数', value: ov.totalDevices || 128, suffix: '台' },
      { label: '在线设备', value: ov.onlineDevices || 122, suffix: '台' },
      { label: '在线率', value: ov.onlineRate || 95.3, suffix: '%' },
      { label: '活跃告警', value: ov.activeAlarms || 3, suffix: '条' },
      { label: '数据点数', value: ov.totalPoints || 512, suffix: '个' }
    ]

    keyPoints.value = ov.keyPoints || generateKeyPoints()
    alarms.value = (alarmRes.data?.list || alarmRes.data || []).length ? (alarmRes.data?.list || alarmRes.data) : generateAlarms()
  } catch (e) {
    keyPoints.value = generateKeyPoints()
    alarms.value = generateAlarms()
  }
}

function generateKeyPoints() {
  return [
    { id: 1, name: 'CH₄浓度-1号井', value: 0.25, unit: '%LEL', status: 'normal', thresholdHigh: 25 },
    { id: 2, name: 'H₂S浓度-2号井', value: 8.5, unit: 'ppm', status: 'warning', thresholdHigh: 10 },
    { id: 3, name: 'CO浓度-3号井', value: 12.3, unit: 'ppm', status: 'normal', thresholdHigh: 24 },
    { id: 4, name: 'O₂浓度-1号井', value: 20.9, unit: '%', status: 'normal', thresholdHigh: 23.5 },
    { id: 5, name: '温度-2号井', value: 36.2, unit: '℃', status: 'alarm', thresholdHigh: 35 },
    { id: 6, name: '压力-1号井', value: 101.3, unit: 'kPa', status: 'normal', thresholdHigh: 120 },
    { id: 7, name: '流速-3号井', value: 5.8, unit: 'm/s', status: 'normal', thresholdHigh: 10 },
    { id: 8, name: '湿度-2号井', value: 65.2, unit: '%', status: 'warning', thresholdHigh: 80 }
  ]
}

function generateAlarms() {
  const now = Date.now()
  return [
    { id: 1, message: '温度传感器读数超过阈值 36.2℃ > 35℃', level: 'critical', createdAt: new Date(now - 120000).toISOString() },
    { id: 2, message: 'H₂S浓度接近预警阈值 8.5ppm', level: 'high', createdAt: new Date(now - 300000).toISOString() },
    { id: 3, message: '湿度传感器读数偏高 65.2%', level: 'medium', createdAt: new Date(now - 600000).toISOString() },
    { id: 4, message: '3号井流速传感器信号弱', level: 'low', createdAt: new Date(now - 900000).toISOString() },
    { id: 5, message: '2号井温湿度传感器电池电量低', level: 'low', createdAt: new Date(now - 1200000).toISOString() }
  ]
}

onMounted(async () => {
  updateTime()
  timeTimer = setInterval(updateTime, 1000)

  await loadData()
  await nextTick()

  initMainChart()
  initDeviceChart()
  initAlarmChart()

  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  if (timeTimer) clearInterval(timeTimer)
  window.removeEventListener('resize', handleResize)
  mainChart?.dispose()
  deviceChart?.dispose()
  alarmChart?.dispose()
})
</script>

<style scoped>
.data-screen {
  background: #0a0e27;
  min-height: 100vh;
  color: #c0c4cc;
  font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif;
  position: fixed;
  inset: 0;
  z-index: 9999;
  overflow-y: auto;
}

.screen-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 24px;
  background: linear-gradient(180deg, rgba(10, 14, 39, 0.95), rgba(10, 14, 39, 0.8));
  border-bottom: 1px solid #1a2550;
}

.logo-area {
  display: flex;
  align-items: center;
  gap: 10px;
}

.logo {
  width: 32px;
  height: 32px;
}

.title {
  font-size: 20px;
  font-weight: 700;
  background: linear-gradient(90deg, #409eff, #67c23a);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  letter-spacing: 2px;
}

.datetime {
  font-size: 16px;
  font-family: 'DIN', 'Courier New', monospace;
  color: #409eff;
  letter-spacing: 2px;
}

.screen-btn {
  background: transparent;
  border: 1px solid #ffffff30;
  color: #c0c4cc;
}

.screen-btn:hover {
  border-color: #409eff;
  color: #409eff;
}

.screen-body {
  padding: 16px 24px;
}

.top-stats {
  display: flex;
  justify-content: space-around;
  margin-bottom: 16px;
  padding: 16px 0;
  background: linear-gradient(180deg, rgba(64, 158, 255, 0.08), transparent);
  border-radius: 8px;
  border: 1px solid #1a2550;
}

.big-stat {
  text-align: center;
}

.big-stat-value {
  display: flex;
  align-items: baseline;
  justify-content: center;
  gap: 4px;
}

.big-stat-value .number {
  font-size: 36px;
  font-weight: 700;
  font-family: 'DIN', 'Courier New', monospace;
  background: linear-gradient(180deg, #ffffff, #409eff);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.big-stat-value .suffix {
  font-size: 14px;
  color: #909399;
}

.big-stat-label {
  font-size: 13px;
  color: #909399;
  margin-top: 4px;
}

.screen-main {
  display: flex;
  gap: 16px;
  height: calc(100vh - 200px);
}

.screen-left, .screen-right {
  width: 280px;
  flex-shrink: 0;
}

.screen-center {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.center-bottom {
  display: flex;
  gap: 16px;
}

.center-bottom .half {
  flex: 1;
}

.panel {
  background: rgba(16, 22, 58, 0.8);
  border: 1px solid #1a2550;
  border-radius: 8px;
  padding: 16px;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.panel-title {
  font-size: 14px;
  font-weight: 600;
  color: #e0e6ed;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #1a2550;
}

.title-icon {
  margin-right: 6px;
}

.main-chart {
  flex: 1;
  min-height: 200px;
}

.small-chart {
  flex: 1;
  min-height: 150px;
}

.alarm-scroll {
  flex: 1;
  overflow-y: auto;
}

.screen-alarm-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 0;
  border-bottom: 1px solid #ffffff08;
  font-size: 13px;
}

.alarm-level-tag {
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 4px;
  flex-shrink: 0;
}

.level-critical .alarm-level-tag { background: #f56c6c30; color: #f56c6c; }
.level-high .alarm-level-tag { background: #e6a23c30; color: #e6a23c; }
.level-medium .alarm-level-tag { background: #409eff30; color: #409eff; }
.level-low .alarm-level-tag { background: #90939930; color: #909399; }

.alarm-text {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.alarm-time {
  font-size: 11px;
  color: #909399;
  flex-shrink: 0;
}

.no-data {
  text-align: center;
  padding: 40px 0;
  color: #909399;
}

.key-points-list {
  flex: 1;
  overflow-y: auto;
}

.key-point-item {
  padding: 10px 0;
  border-bottom: 1px solid #ffffff08;
}

.kp-name {
  font-size: 12px;
  color: #909399;
  margin-bottom: 4px;
}

.kp-value-row {
  display: flex;
  align-items: baseline;
  gap: 4px;
  margin-bottom: 6px;
}

.kp-value {
  font-size: 22px;
  font-weight: 700;
  font-family: 'DIN', 'Courier New', monospace;
}

.kp-unit {
  font-size: 12px;
  color: #909399;
}

.status-normal .kp-value { color: #67c23a; }
.status-warning .kp-value { color: #e6a23c; }
.status-alarm .kp-value { color: #f56c6c; }

.kp-bar {
  height: 4px;
  background: #ffffff10;
  border-radius: 2px;
  overflow: hidden;
}

.kp-bar-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 1s ease;
}

.kp-bar-fill.status-normal { background: #67c23a; }
.kp-bar-fill.status-warning { background: #e6a23c; }
.kp-bar-fill.status-alarm { background: #f56c6c; }
</style>
