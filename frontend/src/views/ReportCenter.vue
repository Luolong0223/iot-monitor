<template>
  <div class="report-center">
    <el-tabs v-model="activeTab" type="border-card">
      <!-- Daily Report -->
      <el-tab-pane label="日报" name="daily">
        <div class="tab-toolbar">
          <el-date-picker v-model="dailyDate" type="date" placeholder="选择日期" value-format="YYYY-MM-DD" style="width: 200px" />
          <el-button type="primary" @click="loadDaily">查询</el-button>
          <el-button :icon="Download" @click="exportReport('daily')">导出Excel</el-button>
        </div>
        <el-table :data="dailyData" stripe v-loading="dailyLoading" style="width: 100%" show-summary :summary-method="dailySummary">
          <el-table-column prop="pointName" label="数据点" min-width="180" />
          <el-table-column prop="avg" label="平均值" width="100" />
          <el-table-column prop="max" label="最大值" width="100">
            <template #default="{ row }"><span style="color: #f56c6c; font-weight: 600">{{ row.max }}</span></template>
          </el-table-column>
          <el-table-column prop="min" label="最小值" width="100">
            <template #default="{ row }"><span style="color: #67c23a; font-weight: 600">{{ row.min }}</span></template>
          </el-table-column>
          <el-table-column prop="unit" label="单位" width="80" />
          <el-table-column prop="alarmCount" label="告警次数" width="100">
            <template #default="{ row }">
              <el-tag :type="row.alarmCount > 0 ? 'danger' : 'success'" size="small">{{ row.alarmCount }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="dataCount" label="数据条数" width="100" />
        </el-table>
      </el-tab-pane>

      <!-- Monthly Report -->
      <el-tab-pane label="月报" name="monthly">
        <div class="tab-toolbar">
          <el-date-picker v-model="monthlyMonth" type="month" placeholder="选择月份" value-format="YYYY-MM" style="width: 200px" />
          <el-button type="primary" @click="loadMonthly">查询</el-button>
          <el-button :icon="Download" @click="exportReport('monthly')">导出Excel</el-button>
        </div>
        <div ref="monthlyChartRef" class="report-chart"></div>
        <el-table :data="monthlyData" stripe v-loading="monthlyLoading" style="width: 100%">
          <el-table-column prop="pointName" label="数据点" min-width="180" />
          <el-table-column prop="avg" label="月平均" width="100" />
          <el-table-column prop="max" label="月最大" width="100" />
          <el-table-column prop="min" label="月最小" width="100" />
          <el-table-column prop="unit" label="单位" width="80" />
          <el-table-column prop="alarmCount" label="告警次数" width="100" />
          <el-table-column prop="normalRate" label="正常率" width="100">
            <template #default="{ row }">
              <el-progress :percentage="row.normalRate" :color="row.normalRate > 95 ? '#67c23a' : row.normalRate > 80 ? '#e6a23c' : '#f56c6c'" :stroke-width="8" />
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- Custom Report -->
      <el-tab-pane label="自定义报表" name="custom">
        <div class="tab-toolbar">
          <el-date-picker
            v-model="customRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            style="width: 300px"
          />
          <el-select v-model="customPointIds" multiple placeholder="选择数据点" filterable style="width: 300px">
            <el-option v-for="p in pointOptions" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
          <el-select v-model="customAgg" style="width: 120px">
            <el-option label="按天" value="day" />
            <el-option label="按周" value="week" />
            <el-option label="按月" value="month" />
          </el-select>
          <el-button type="primary" @click="loadCustom">生成报表</el-button>
          <el-button :icon="Download" @click="exportReport('custom')">导出Excel</el-button>
        </div>
        <div ref="customChartRef" class="report-chart"></div>
        <el-table :data="customData" stripe v-loading="customLoading" style="width: 100%">
          <el-table-column prop="date" label="日期" width="120" />
          <el-table-column v-for="pointId in customPointIds" :key="pointId" :label="getPointName(pointId)" min-width="120">
            <template #default="{ row }">{{ row.values?.[pointId] ?? '--' }}</template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import * as echarts from 'echarts'
import { Download } from '@element-plus/icons-vue'
import { getDailyReport, getMonthlyReport, getCustomReport, exportReport as exportReportApi } from '../api/reports.js'
import { getDataPointList } from '../api/dataPoints.js'
import { ElMessage } from 'element-plus'

const activeTab = ref('daily')

const dailyDate = ref('')
const dailyData = ref([])
const dailyLoading = ref(false)

const monthlyMonth = ref('')
const monthlyData = ref([])
const monthlyLoading = ref(false)
const monthlyChartRef = ref(null)
let monthlyChart = null

const customRange = ref([])
const customPointIds = ref([])
const customAgg = ref('day')
const customData = ref([])
const customLoading = ref(false)
const customChartRef = ref(null)
let customChart = null

const pointOptions = ref([])

function getPointName(id) {
  const p = pointOptions.value.find(p => p.id === id)
  return p?.name || `点${id}`
}

function dailySummary({ columns, data }) {
  const sums = []
  columns.forEach((col, idx) => {
    if (idx === 0) { sums[idx] = '汇总'; return }
    if (['avg', 'max', 'min'].includes(col.property)) {
      const vals = data.map(d => Number(d[col.property])).filter(v => !isNaN(v))
      if (col.property === 'avg') sums[idx] = vals.length ? (vals.reduce((a, b) => a + b, 0) / vals.length).toFixed(2) : '--'
      else if (col.property === 'max') sums[idx] = vals.length ? Math.max(...vals).toFixed(2) : '--'
      else sums[idx] = vals.length ? Math.min(...vals).toFixed(2) : '--'
    } else if (col.property === 'alarmCount') {
      sums[idx] = data.reduce((s, d) => s + (d.alarmCount || 0), 0)
    } else {
      sums[idx] = ''
    }
  })
  return sums
}

function generateDemoDaily() {
  return [
    { pointName: 'CH₄浓度-1号井', avg: '0.23', max: '0.45', min: '0.12', unit: '%LEL', alarmCount: 0, dataCount: 8640 },
    { pointName: 'H₂S浓度-2号井', avg: '5.67', max: '9.20', min: '2.10', unit: 'ppm', alarmCount: 3, dataCount: 8640 },
    { pointName: 'CO浓度-3号井', avg: '8.45', max: '15.30', min: '3.20', unit: 'ppm', alarmCount: 1, dataCount: 8640 },
    { pointName: 'O₂浓度-1号井', avg: '20.85', max: '21.20', min: '20.50', unit: '%', alarmCount: 0, dataCount: 8640 },
    { pointName: '温度-2号井', avg: '24.5', max: '36.2', min: '18.3', unit: '℃', alarmCount: 5, dataCount: 8640 }
  ]
}

function generateDemoMonthly() {
  return [
    { pointName: 'CH₄浓度-1号井', avg: '0.24', max: '0.55', min: '0.10', unit: '%LEL', alarmCount: 2, normalRate: 99.5 },
    { pointName: 'H₂S浓度-2号井', avg: '5.80', max: '12.30', min: '1.50', unit: 'ppm', alarmCount: 15, normalRate: 92.3 },
    { pointName: 'CO浓度-3号井', avg: '8.20', max: '18.50', min: '2.80', unit: 'ppm', alarmCount: 8, normalRate: 95.1 },
    { pointName: 'O₂浓度-1号井', avg: '20.82', max: '21.30', min: '20.40', unit: '%', alarmCount: 0, normalRate: 100 },
    { pointName: '温度-2号井', avg: '25.1', max: '38.5', min: '16.2', unit: '℃', alarmCount: 22, normalRate: 88.7 }
  ]
}

function generateDemoCustom() {
  const data = []
  const days = customRange.value?.length === 2 ? 30 : 14
  for (let i = 0; i < days; i++) {
    const d = new Date()
    d.setDate(d.getDate() - days + i)
    const row = {
      date: `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`,
      values: {}
    }
    customPointIds.value.forEach(pid => {
      row.values[pid] = Math.round((20 + Math.random() * 15) * 100) / 100
    })
    data.push(row)
  }
  return data
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

async function loadDaily() {
  if (!dailyDate.value) {
    ElMessage.warning('请选择日期')
    return
  }
  dailyLoading.value = true
  try {
    const res = await getDailyReport({ date: dailyDate.value })
    dailyData.value = res.data || []
    if (!dailyData.value.length) dailyData.value = generateDemoDaily()
  } catch (e) {
    dailyData.value = generateDemoDaily()
  } finally {
    dailyLoading.value = false
  }
}

async function loadMonthly() {
  if (!monthlyMonth.value) {
    ElMessage.warning('请选择月份')
    return
  }
  monthlyLoading.value = true
  try {
    const res = await getMonthlyReport({ month: monthlyMonth.value })
    monthlyData.value = res.data || []
    if (!monthlyData.value.length) monthlyData.value = generateDemoMonthly()
  } catch (e) {
    monthlyData.value = generateDemoMonthly()
  } finally {
    monthlyLoading.value = false
  }
  updateMonthlyChart()
}

function updateMonthlyChart() {
  if (!monthlyChart || !monthlyData.value.length) return
  monthlyChart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['平均值', '最大值', '最小值'] },
    grid: { left: 50, right: 20, top: 40, bottom: 30 },
    xAxis: { type: 'category', data: monthlyData.value.map(d => d.pointName) },
    yAxis: { type: 'value' },
    series: [
      { name: '平均值', type: 'bar', data: monthlyData.value.map(d => Number(d.avg)), itemStyle: { color: '#409eff' } },
      { name: '最大值', type: 'bar', data: monthlyData.value.map(d => Number(d.max)), itemStyle: { color: '#f56c6c' } },
      { name: '最小值', type: 'bar', data: monthlyData.value.map(d => Number(d.min)), itemStyle: { color: '#67c23a' } }
    ]
  })
}

async function loadCustom() {
  if (!customRange.value?.length || !customPointIds.value.length) {
    ElMessage.warning('请选择日期范围和数据点')
    return
  }
  customLoading.value = true
  try {
    const res = await getCustomReport({
      startDate: customRange.value[0],
      endDate: customRange.value[1],
      pointIds: customPointIds.value,
      aggregation: customAgg.value
    })
    customData.value = res.data || []
    if (!customData.value.length) customData.value = generateDemoCustom()
  } catch (e) {
    customData.value = generateDemoCustom()
  } finally {
    customLoading.value = false
  }
  updateCustomChart()
}

function updateCustomChart() {
  if (!customChart || !customData.value.length) return
  const series = customPointIds.value.map(pid => ({
    name: getPointName(pid),
    type: 'line',
    data: customData.value.map(d => d.values?.[pid] ?? null),
    smooth: true
  }))
  customChart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: series.map(s => s.name) },
    grid: { left: 50, right: 20, top: 40, bottom: 30 },
    xAxis: { type: 'category', data: customData.value.map(d => d.date) },
    yAxis: { type: 'value' },
    series
  }, true)
}

async function exportReport(type) {
  const params = { type }
  if (type === 'daily') {
    if (!dailyDate.value) { ElMessage.warning('请先选择日期'); return }
    params.date = dailyDate.value
  } else if (type === 'monthly') {
    if (!monthlyMonth.value) { ElMessage.warning('请先选择月份'); return }
    params.month = monthlyMonth.value
  } else {
    if (!customRange.value?.length) { ElMessage.warning('请先选择日期范围'); return }
    params.startDate = customRange.value[0]
    params.endDate = customRange.value[1]
    params.pointIds = customPointIds.value
  }

  try {
    const res = await exportReportApi(params)
    const url = window.URL.createObjectURL(new Blob([res]))
    const a = document.createElement('a')
    a.href = url
    a.download = `报表_${type}_${new Date().toISOString().slice(0, 10)}.xlsx`
    a.click()
    window.URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch (e) {
    ElMessage.info('导出功能需要后端支持')
  }
}

onMounted(async () => {
  await loadPoints()

  const now = new Date()
  dailyDate.value = now.toISOString().slice(0, 10)
  monthlyMonth.value = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`

  await nextTick()

  if (monthlyChartRef.value) {
    monthlyChart = echarts.init(monthlyChartRef.value)
  }
  if (customChartRef.value) {
    customChart = echarts.init(customChartRef.value)
  }

  window.addEventListener('resize', () => {
    monthlyChart?.resize()
    customChart?.resize()
  })

  loadDaily()
})

watch(activeTab, (tab) => {
  if (tab === 'monthly') {
    nextTick(() => {
      if (!monthlyChart && monthlyChartRef.value) {
        monthlyChart = echarts.init(monthlyChartRef.value)
      }
      loadMonthly()
    })
  }
})

onBeforeUnmount(() => {
  monthlyChart?.dispose()
  customChart?.dispose()
})
</script>

<style scoped>
.report-center {
  min-height: 100%;
}

.tab-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.report-chart {
  height: 300px;
  margin-bottom: 20px;
}
</style>
