<template>
  <div class="history-page">
    <!-- Filter Form -->
    <el-card shadow="hover" class="filter-card">
      <el-form :model="filter" inline class="filter-form">
        <el-form-item label="层级">
          <el-cascader
            v-model="filter.hierarchyPath"
            :options="hierarchyOptions"
            :props="{ checkStrictly: true, value: 'id', label: 'name', children: 'children' }"
            placeholder="选择层级"
            clearable
            style="width: 200px"
          />
        </el-form-item>
        <el-form-item label="数据点">
          <el-select v-model="filter.pointId" placeholder="选择数据点" clearable filterable style="width: 200px">
            <el-option v-for="p in pointOptions" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="时间范围">
          <el-date-picker
            v-model="filter.timeRange"
            type="datetimerange"
            range-separator="至"
            start-placeholder="开始时间"
            end-placeholder="结束时间"
            value-format="YYYY-MM-DDTHH:mm:ss"
            :shortcuts="timeShortcuts"
            style="width: 360px"
          />
        </el-form-item>
        <el-form-item label="聚合">
          <el-select v-model="filter.aggregation" style="width: 120px">
            <el-option label="原始数据" value="raw" />
            <el-option label="1分钟" value="1m" />
            <el-option label="5分钟" value="5m" />
            <el-option label="15分钟" value="15m" />
            <el-option label="1小时" value="1h" />
            <el-option label="1天" value="1d" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="loadData">查询</el-button>
          <el-button :icon="Download" @click="handleExport">导出</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- Statistics -->
    <el-row :gutter="20" class="stats-row">
      <el-col :xs="12" :sm="6">
        <div class="mini-stat">
          <div class="mini-stat-label">平均值</div>
          <div class="mini-stat-value">{{ stats.avg }}</div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6">
        <div class="mini-stat">
          <div class="mini-stat-label">最大值</div>
          <div class="mini-stat-value" style="color: #f56c6c">{{ stats.max }}</div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6">
        <div class="mini-stat">
          <div class="mini-stat-label">最小值</div>
          <div class="mini-stat-value" style="color: #67c23a">{{ stats.min }}</div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6">
        <div class="mini-stat">
          <div class="mini-stat-label">数据条数</div>
          <div class="mini-stat-value">{{ stats.count }}</div>
        </div>
      </el-col>
    </el-row>

    <!-- Chart -->
    <el-card shadow="hover" class="chart-card">
      <template #header><span>数据趋势</span></template>
      <div ref="chartRef" class="chart-container"></div>
    </el-card>

    <!-- Data Table -->
    <el-card shadow="hover" style="margin-top: 20px">
      <template #header><span>数据列表</span></template>
      <el-table :data="tableData" stripe v-loading="loading" style="width: 100%" max-height="500">
        <el-table-column type="index" label="#" width="60" />
        <el-table-column prop="time" label="时间" width="180">
          <template #default="{ row }">{{ formatTime(row.time) }}</template>
        </el-table-column>
        <el-table-column prop="value" label="数值" width="120">
          <template #default="{ row }">
            <span style="font-weight: 600">{{ row.value }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="unit" label="单位" width="80" />
        <el-table-column prop="pointName" label="数据点" min-width="180" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusTag(row.status)" size="small">{{ statusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[20, 50, 100, 200]"
          layout="total, sizes, prev, pager, next, jumper"
          @current-change="loadData"
          @size-change="loadData"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as echarts from 'echarts'
import { Search, Download } from '@element-plus/icons-vue'
import { queryHistory, exportHistory, getHistoryStatistics } from '../api/history.js'
import { getHierarchyTree } from '../api/hierarchy.js'
import { getDataPointList } from '../api/dataPoints.js'
import { ElMessage } from 'element-plus'

const chartRef = ref(null)
const loading = ref(false)
let chart = null

const filter = ref({
  hierarchyPath: [],
  pointId: '',
  timeRange: [],
  aggregation: 'raw'
})

const timeShortcuts = [
  { text: '最近1小时', value: () => { const e = new Date(); const s = new Date(e - 3600000); return [s, e] } },
  { text: '最近6小时', value: () => { const e = new Date(); const s = new Date(e - 21600000); return [s, e] } },
  { text: '最近24小时', value: () => { const e = new Date(); const s = new Date(e - 86400000); return [s, e] } },
  { text: '最近7天', value: () => { const e = new Date(); const s = new Date(e - 604800000); return [s, e] } },
  { text: '最近30天', value: () => { const e = new Date(); const s = new Date(e - 2592000000); return [s, e] } }
]

const hierarchyOptions = ref([])
const pointOptions = ref([])
const tableData = ref([])
const page = ref(1)
const pageSize = ref(50)
const total = ref(0)
const stats = ref({ avg: '--', max: '--', min: '--', count: 0 })

function formatTime(t) {
  if (!t) return '-'
  return new Date(t).toLocaleString('zh-CN', { hour12: false })
}

function statusTag(s) {
  const m = { normal: 'success', warning: 'warning', alarm: 'danger', offline: 'info' }
  return m[s] || 'info'
}

function statusText(s) {
  const m = { normal: '正常', warning: '预警', alarm: '告警', offline: '离线' }
  return m[s] || s
}

async function loadHierarchy() {
  try {
    const res = await getHierarchyTree()
    hierarchyOptions.value = res.data || []
  } catch (e) {
    hierarchyOptions.value = [
      { id: 1, name: '一号矿区', children: [{ id: 11, name: '1号井' }, { id: 12, name: '2号井' }] },
      { id: 2, name: '二号矿区', children: [{ id: 21, name: '3号井' }, { id: 22, name: '4号井' }] }
    ]
  }
}

async function loadPoints() {
  try {
    const res = await getDataPointList({ pageSize: 1000 })
    pointOptions.value = res.data?.list || res.data || []
  } catch (e) {
    pointOptions.value = [
      { id: 1, name: 'CH₄浓度-1号井' }, { id: 2, name: 'H₂S浓度-2号井' },
      { id: 3, name: 'CO浓度-3号井' }, { id: 4, name: 'O₂浓度-1号井' }
    ]
  }
}

async function loadData() {
  loading.value = true
  const params = {
    page: page.value,
    pageSize: pageSize.value,
    aggregation: filter.value.aggregation
  }
  if (filter.value.pointId) params.pointId = filter.value.pointId
  if (filter.value.hierarchyPath?.length) params.hierarchyId = filter.value.hierarchyPath[filter.value.hierarchyPath.length - 1]
  if (filter.value.timeRange?.length === 2) {
    params.startTime = filter.value.timeRange[0]
    params.endTime = filter.value.timeRange[1]
  }

  try {
    const [historyRes, statsRes] = await Promise.all([
      queryHistory(params),
      getHistoryStatistics(params).catch(() => ({ data: null }))
    ])

    const data = historyRes.data?.list || historyRes.data || []
    tableData.value = data.length ? data : generateDemoData()
    total.value = historyRes.data?.total || tableData.value.length

    const s = statsRes?.data || {}
    const values = tableData.value.map(d => d.value).filter(v => v != null)
    stats.value = {
      avg: s.avg ?? (values.length ? (values.reduce((a, b) => a + b, 0) / values.length).toFixed(2) : '--'),
      max: s.max ?? (values.length ? Math.max(...values).toFixed(2) : '--'),
      min: s.min ?? (values.length ? Math.min(...values).toFixed(2) : '--'),
      count: s.count ?? values.length
    }

    updateChart(tableData.value)
  } catch (e) {
    tableData.value = generateDemoData()
    total.value = tableData.value.length
    updateChart(tableData.value)
  } finally {
    loading.value = false
  }
}

function generateDemoData() {
  const now = Date.now()
  return Array.from({ length: 100 }, (_, i) => ({
    time: new Date(now - (100 - i) * 60000).toISOString(),
    value: Math.round((20 + Math.random() * 15 + Math.sin(i / 10) * 5) * 100) / 100,
    unit: 'ppm',
    pointName: 'CH₄浓度-1号井',
    status: Math.random() > 0.9 ? 'warning' : 'normal'
  }))
}

function updateChart(data) {
  if (!chart) return
  const times = data.map(d => {
    const dt = new Date(d.time)
    return `${String(dt.getMonth() + 1).padStart(2, '0')}/${String(dt.getDate()).padStart(2, '0')} ${String(dt.getHours()).padStart(2, '0')}:${String(dt.getMinutes()).padStart(2, '0')}`
  })
  const values = data.map(d => d.value)

  chart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 50, right: 20, top: 20, bottom: 50 },
    dataZoom: [{ type: 'inside' }, { type: 'slider', bottom: 5 }],
    xAxis: { type: 'category', data: times, boundaryGap: false },
    yAxis: { type: 'value' },
    series: [{
      type: 'line',
      data: values,
      smooth: true,
      lineStyle: { width: 1.5, color: '#409eff' },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(64, 158, 255, 0.25)' },
          { offset: 1, color: 'rgba(64, 158, 255, 0.02)' }
        ])
      },
      itemStyle: { color: '#409eff' },
      showSymbol: false
    }]
  }, true)
}

async function handleExport() {
  const params = {
    aggregation: filter.value.aggregation,
    format: 'xlsx'
  }
  if (filter.value.pointId) params.pointId = filter.value.pointId
  if (filter.value.timeRange?.length === 2) {
    params.startTime = filter.value.timeRange[0]
    params.endTime = filter.value.timeRange[1]
  }

  try {
    const res = await exportHistory(params)
    const url = window.URL.createObjectURL(new Blob([res]))
    const a = document.createElement('a')
    a.href = url
    a.download = `历史数据_${new Date().toISOString().slice(0, 10)}.xlsx`
    a.click()
    window.URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch (e) {
    ElMessage.info('导出功能需要后端支持')
  }
}

onMounted(async () => {
  await Promise.all([loadHierarchy(), loadPoints()])
  await nextTick()

  if (chartRef.value) {
    chart = echarts.init(chartRef.value)
    window.addEventListener('resize', () => chart?.resize())
  }

  // Default: last 24 hours
  const now = new Date()
  filter.value.timeRange = [new Date(now - 86400000).toISOString(), now.toISOString()]
  loadData()
})

onBeforeUnmount(() => {
  chart?.dispose()
})
</script>

<style scoped>
.history-page {
  min-height: 100%;
}

.filter-card {
  margin-bottom: 20px;
}

.filter-form {
  display: flex;
  flex-wrap: wrap;
  gap: 0;
}

.stats-row {
  margin-bottom: 20px;
}

.mini-stat {
  background: #fff;
  border-radius: 8px;
  padding: 16px 20px;
  text-align: center;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
}

.mini-stat-label {
  font-size: 13px;
  color: #909399;
  margin-bottom: 8px;
}

.mini-stat-value {
  font-size: 24px;
  font-weight: 700;
  font-family: 'DIN', 'Helvetica Neue', monospace;
  color: #303133;
}

.chart-container {
  height: 350px;
}

.pagination-wrap {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
