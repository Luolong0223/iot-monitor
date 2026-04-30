<template>
  <div class="alarm-center">
    <el-tabs v-model="activeTab" type="border-card">
      <!-- Real-time Alarms -->
      <el-tab-pane label="实时告警" name="realtime">
        <div class="tab-toolbar">
          <el-input v-model="searchText" placeholder="搜索告警..." prefix-icon="Search" clearable style="width: 260px" />
          <el-select v-model="levelFilter" placeholder="告警级别" clearable style="width: 140px">
            <el-option label="全部" value="" />
            <el-option label="紧急" value="critical" />
            <el-option label="高" value="high" />
            <el-option label="中" value="medium" />
            <el-option label="低" value="low" />
          </el-select>
          <el-button type="primary" :icon="Refresh" @click="loadRealtime">刷新</el-button>
          <el-button type="warning" :disabled="!selectedAlarms.length" @click="batchAck">批量确认</el-button>
          <div class="toolbar-right">
            <el-switch v-model="soundEnabled" active-text="声音告警" inactive-text="" style="margin-right: 12px" />
            <span class="alarm-count">共 {{ realtimeAlarms.length }} 条未处理</span>
          </div>
        </div>

        <el-table
          :data="filteredRealtime"
          stripe
          v-loading="realtimeLoading"
          @selection-change="handleSelectionChange"
          style="width: 100%"
          :row-class-name="alarmRowClass"
        >
          <el-table-column type="selection" width="50" />
          <el-table-column prop="level" label="级别" width="80">
            <template #default="{ row }">
              <el-tag :type="levelTagType(row.level)" size="small" effect="dark">{{ levelText(row.level) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="message" label="告警信息" min-width="250" />
          <el-table-column prop="pointName" label="数据点" width="180" />
          <el-table-column prop="deviceName" label="设备" width="150" />
          <el-table-column prop="value" label="当前值" width="100">
            <template #default="{ row }">
              <span style="font-weight: 600; color: #f56c6c">{{ row.value }} {{ row.unit }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="threshold" label="阈值" width="120">
            <template #default="{ row }">{{ row.thresholdLow }} ~ {{ row.thresholdHigh }}</template>
          </el-table-column>
          <el-table-column prop="createdAt" label="发生时间" width="180">
            <template #default="{ row }">{{ formatTime(row.createdAt) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="120" fixed="right">
            <template #default="{ row }">
              <el-button type="primary" link size="small" @click="ackAlarm(row)">确认</el-button>
              <el-button type="success" link size="small" @click="resolveAlarm(row)">解决</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- Alarm History -->
      <el-tab-pane label="告警历史" name="history">
        <div class="tab-toolbar">
          <el-date-picker
            v-model="historyTimeRange"
            type="datetimerange"
            range-separator="至"
            start-placeholder="开始"
            end-placeholder="结束"
            value-format="YYYY-MM-DDTHH:mm:ss"
            style="width: 360px"
          />
          <el-select v-model="historyLevelFilter" placeholder="告警级别" clearable style="width: 140px">
            <el-option label="全部" value="" />
            <el-option label="紧急" value="critical" />
            <el-option label="高" value="high" />
            <el-option label="中" value="medium" />
            <el-option label="低" value="low" />
          </el-select>
          <el-select v-model="historyStatusFilter" placeholder="处理状态" clearable style="width: 140px">
            <el-option label="全部" value="" />
            <el-option label="未确认" value="active" />
            <el-option label="已确认" value="acknowledged" />
            <el-option label="已解决" value="resolved" />
          </el-select>
          <el-button type="primary" @click="loadHistory">查询</el-button>
        </div>

        <el-table :data="historyAlarms" stripe v-loading="historyLoading" style="width: 100%">
          <el-table-column prop="level" label="级别" width="80">
            <template #default="{ row }">
              <el-tag :type="levelTagType(row.level)" size="small">{{ levelText(row.level) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="message" label="告警信息" min-width="250" />
          <el-table-column prop="pointName" label="数据点" width="180" />
          <el-table-column prop="status" label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="alarmStatusTag(row.status)" size="small">{{ alarmStatusText(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="createdAt" label="发生时间" width="180">
            <template #default="{ row }">{{ formatTime(row.createdAt) }}</template>
          </el-table-column>
          <el-table-column prop="acknowledgedAt" label="确认时间" width="180">
            <template #default="{ row }">{{ formatTime(row.acknowledgedAt) }}</template>
          </el-table-column>
          <el-table-column prop="resolvedAt" label="解决时间" width="180">
            <template #default="{ row }">{{ formatTime(row.resolvedAt) }}</template>
          </el-table-column>
          <el-table-column prop="acknowledgedBy" label="确认人" width="100" />
        </el-table>
        <div class="pagination-wrap">
          <el-pagination
            v-model:current-page="historyPage"
            v-model:page-size="historyPageSize"
            :total="historyTotal"
            :page-sizes="[20, 50, 100]"
            layout="total, sizes, prev, pager, next"
            @current-change="loadHistory"
            @size-change="loadHistory"
          />
        </div>
      </el-tab-pane>

      <!-- Alarm Config -->
      <el-tab-pane label="告警配置" name="config">
        <div class="tab-toolbar">
          <el-button type="primary" @click="openConfigDialog()">新增规则</el-button>
        </div>

        <el-table :data="alarmConfigs" stripe v-loading="configLoading" style="width: 100%">
          <el-table-column prop="name" label="规则名称" min-width="180" />
          <el-table-column prop="pointName" label="数据点" width="180" />
          <el-table-column prop="condition" label="条件" width="200">
            <template #default="{ row }">
              {{ row.operator }} {{ row.threshold }} {{ row.unit }}
            </template>
          </el-table-column>
          <el-table-column prop="level" label="级别" width="80">
            <template #default="{ row }">
              <el-tag :type="levelTagType(row.level)" size="small">{{ levelText(row.level) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="enabled" label="状态" width="80">
            <template #default="{ row }">
              <el-switch v-model="row.enabled" @change="toggleConfig(row)" />
            </template>
          </el-table-column>
          <el-table-column label="操作" width="140">
            <template #default="{ row }">
              <el-button type="primary" link size="small" @click="openConfigDialog(row)">编辑</el-button>
              <el-button type="danger" link size="small" @click="deleteConfig(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <!-- Config Dialog -->
    <el-dialog v-model="configDialogVisible" :title="configForm.id ? '编辑告警规则' : '新增告警规则'" width="500px">
      <el-form ref="configFormRef" :model="configForm" :rules="configRules" label-width="100px">
        <el-form-item label="规则名称" prop="name">
          <el-input v-model="configForm.name" placeholder="如：CH₄浓度超限告警" />
        </el-form-item>
        <el-form-item label="数据点" prop="pointId">
          <el-select v-model="configForm.pointId" placeholder="选择数据点" filterable style="width: 100%">
            <el-option v-for="p in pointOptions" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="条件" prop="operator">
          <el-col :span="11">
            <el-select v-model="configForm.operator" style="width: 100%">
              <el-option label="大于 (>)" value=">" />
              <el-option label="小于 (<)" value="<" />
              <el-option label="大于等于 (≥)" value=">=" />
              <el-option label="小于等于 (≤)" value="<=" />
              <el-option label="等于 (=)" value="==" />
            </el-select>
          </el-col>
          <el-col :span="2" style="text-align: center">-</el-col>
          <el-col :span="11">
            <el-input-number v-model="configForm.threshold" :precision="2" style="width: 100%" />
          </el-col>
        </el-form-item>
        <el-form-item label="告警级别" prop="level">
          <el-select v-model="configForm.level" style="width: 100%">
            <el-option label="紧急" value="critical" />
            <el-option label="高" value="high" />
            <el-option label="中" value="medium" />
            <el-option label="低" value="low" />
          </el-select>
        </el-form-item>
        <el-form-item label="通知方式">
          <el-checkbox-group v-model="configForm.notifyMethods">
            <el-checkbox label="web">站内通知</el-checkbox>
            <el-checkbox label="email">邮件</el-checkbox>
            <el-checkbox label="sms">短信</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="configForm.enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="configDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="configSaving" @click="saveConfig">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { Search, Refresh } from '@element-plus/icons-vue'
import { getAlarmList, acknowledgeAlarm, resolveAlarm, batchAcknowledgeAlarms, getAlarmConfig, updateAlarmConfig, createAlarmConfig, deleteAlarmConfig as deleteAlarmConfigApi } from '../api/alarms.js'
import { getDataPointList } from '../api/dataPoints.js'
import { WebSocketManager } from '../utils/websocket.js'
import { ElMessage, ElMessageBox } from 'element-plus'

const activeTab = ref('realtime')
const searchText = ref('')
const levelFilter = ref('')
const soundEnabled = ref(true)
const selectedAlarms = ref([])

const realtimeAlarms = ref([])
const realtimeLoading = ref(false)

const historyAlarms = ref([])
const historyLoading = ref(false)
const historyTimeRange = ref([])
const historyLevelFilter = ref('')
const historyStatusFilter = ref('')
const historyPage = ref(1)
const historyPageSize = ref(20)
const historyTotal = ref(0)

const alarmConfigs = ref([])
const configLoading = ref(false)
const configDialogVisible = ref(false)
const configSaving = ref(false)
const configFormRef = ref(null)
const configForm = ref({ id: null, name: '', pointId: '', operator: '>', threshold: 0, level: 'medium', notifyMethods: ['web'], enabled: true })
const configRules = {
  name: [{ required: true, message: '请输入规则名称', trigger: 'blur' }],
  pointId: [{ required: true, message: '请选择数据点', trigger: 'change' }],
  operator: [{ required: true, message: '请选择条件', trigger: 'change' }],
  level: [{ required: true, message: '请选择告警级别', trigger: 'change' }]
}

const pointOptions = ref([])
let wsManager = null
let audio = null

const filteredRealtime = computed(() => {
  let list = realtimeAlarms.value
  if (searchText.value) {
    const q = searchText.value.toLowerCase()
    list = list.filter(a => (a.message || '').toLowerCase().includes(q) || (a.pointName || '').toLowerCase().includes(q))
  }
  if (levelFilter.value) {
    list = list.filter(a => a.level === levelFilter.value)
  }
  return list
})

function formatTime(t) {
  if (!t) return '-'
  return new Date(t).toLocaleString('zh-CN', { hour12: false })
}

function levelText(l) {
  const m = { critical: '紧急', high: '高', medium: '中', low: '低' }
  return m[l] || l
}

function levelTagType(l) {
  const m = { critical: 'danger', high: 'warning', medium: '', low: 'info' }
  return m[l] || 'info'
}

function alarmRowClass({ row }) {
  if (row.level === 'critical') return 'alarm-critical-row'
  if (row.level === 'high') return 'alarm-high-row'
  return ''
}

function alarmStatusTag(s) {
  const m = { active: 'danger', acknowledged: 'warning', resolved: 'success' }
  return m[s] || 'info'
}

function alarmStatusText(s) {
  const m = { active: '未确认', acknowledged: '已确认', resolved: '已解决' }
  return m[s] || s
}

function handleSelectionChange(rows) {
  selectedAlarms.value = rows
}

function playAlarmSound() {
  if (!soundEnabled.value) return
  try {
    if (!audio) {
      audio = new Audio('data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAIA+AAACABAAZGllcw==')
    }
    audio.play().catch(() => {})
  } catch (e) { /* ignore */ }
}

async function loadRealtime() {
  realtimeLoading.value = true
  try {
    const res = await getAlarmList({ page: 1, pageSize: 100, status: 'active' })
    realtimeAlarms.value = res.data?.list || res.data || []
    if (!realtimeAlarms.value.length) {
      realtimeAlarms.value = generateDemoRealtime()
    }
  } catch (e) {
    realtimeAlarms.value = generateDemoRealtime()
  } finally {
    realtimeLoading.value = false
  }
}

async function loadHistory() {
  historyLoading.value = true
  const params = {
    page: historyPage.value,
    pageSize: historyPageSize.value
  }
  if (historyLevelFilter.value) params.level = historyLevelFilter.value
  if (historyStatusFilter.value) params.status = historyStatusFilter.value
  if (historyTimeRange.value?.length === 2) {
    params.startTime = historyTimeRange.value[0]
    params.endTime = historyTimeRange.value[1]
  }

  try {
    const res = await getAlarmList(params)
    historyAlarms.value = res.data?.list || res.data || []
    historyTotal.value = res.data?.total || historyAlarms.value.length
    if (!historyAlarms.value.length) {
      historyAlarms.value = generateDemoHistory()
      historyTotal.value = historyAlarms.value.length
    }
  } catch (e) {
    historyAlarms.value = generateDemoHistory()
    historyTotal.value = historyAlarms.value.length
  } finally {
    historyLoading.value = false
  }
}

async function loadConfigs() {
  configLoading.value = true
  try {
    const res = await getAlarmConfig()
    alarmConfigs.value = res.data?.list || res.data || []
    if (!alarmConfigs.value.length) {
      alarmConfigs.value = generateDemoConfigs()
    }
  } catch (e) {
    alarmConfigs.value = generateDemoConfigs()
  } finally {
    configLoading.value = false
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

async function ackAlarm(row) {
  try {
    await acknowledgeAlarm(row.id)
    ElMessage.success('已确认')
    loadRealtime()
  } catch (e) { /* handled */ }
}

async function resolveAlarm(row) {
  try {
    await resolveAlarm(row.id)
    ElMessage.success('已解决')
    loadRealtime()
  } catch (e) { /* handled */ }
}

async function batchAck() {
  try {
    await ElMessageBox.confirm(`确认批量处理 ${selectedAlarms.value.length} 条告警？`, '提示')
    await batchAcknowledgeAlarms({ ids: selectedAlarms.value.map(a => a.id) })
    ElMessage.success('批量确认成功')
    loadRealtime()
  } catch (e) { /* cancelled or error */ }
}

function openConfigDialog(row) {
  if (row) {
    configForm.value = { ...row, notifyMethods: row.notifyMethods || ['web'] }
  } else {
    configForm.value = { id: null, name: '', pointId: '', operator: '>', threshold: 0, level: 'medium', notifyMethods: ['web'], enabled: true }
  }
  configDialogVisible.value = true
}

async function saveConfig() {
  try {
    await configFormRef.value.validate()
  } catch { return }

  configSaving.value = true
  try {
    if (configForm.value.id) {
      await updateAlarmConfig(configForm.value.id, configForm.value)
    } else {
      await createAlarmConfig(configForm.value)
    }
    ElMessage.success('保存成功')
    configDialogVisible.value = false
    loadConfigs()
  } catch (e) { /* handled */ } finally {
    configSaving.value = false
  }
}

async function toggleConfig(row) {
  try {
    await updateAlarmConfig(row.id, { enabled: row.enabled })
    ElMessage.success(row.enabled ? '已启用' : '已禁用')
  } catch (e) {
    row.enabled = !row.enabled
  }
}

async function deleteConfig(row) {
  try {
    await ElMessageBox.confirm('确认删除该告警规则？', '提示')
    await deleteAlarmConfigApi(row.id)
    ElMessage.success('已删除')
    loadConfigs()
  } catch (e) { /* cancelled */ }
}

function generateDemoRealtime() {
  const now = Date.now()
  return [
    { id: 1, level: 'critical', message: '温度传感器读数超过阈值 36.2℃ > 35℃', pointName: '温度-2号井', deviceName: '温湿度传感器E', value: 36.2, unit: '℃', thresholdLow: 15, thresholdHigh: 35, createdAt: new Date(now - 120000).toISOString() },
    { id: 2, level: 'high', message: 'H₂S浓度接近预警阈值 8.5ppm', pointName: 'H₂S浓度-2号井', deviceName: '硫化氢传感器B', value: 8.5, unit: 'ppm', thresholdLow: 0, thresholdHigh: 10, createdAt: new Date(now - 300000).toISOString() },
    { id: 3, level: 'medium', message: '湿度传感器读数偏高 65.2%', pointName: '湿度-2号井', deviceName: '湿度传感器H', value: 65.2, unit: '%', thresholdLow: 30, thresholdHigh: 80, createdAt: new Date(now - 600000).toISOString() }
  ]
}

function generateDemoHistory() {
  const now = Date.now()
  return Array.from({ length: 10 }, (_, i) => ({
    id: 100 + i,
    level: ['critical', 'high', 'medium', 'low'][i % 4],
    message: ['温度超过阈值', 'H₂S浓度偏高', 'CO浓度预警', '传感器信号弱'][i % 4],
    pointName: ['温度-2号井', 'H₂S浓度-2号井', 'CO浓度-3号井', '流速-3号井'][i % 4],
    status: ['resolved', 'acknowledged', 'active'][i % 3],
    createdAt: new Date(now - (i + 1) * 3600000).toISOString(),
    acknowledgedAt: i % 3 !== 2 ? new Date(now - i * 3600000).toISOString() : null,
    resolvedAt: i % 3 === 0 ? new Date(now - i * 1800000).toISOString() : null,
    acknowledgedBy: i % 3 !== 2 ? 'admin' : null
  }))
}

function generateDemoConfigs() {
  return [
    { id: 1, name: 'CH₄浓度超限告警', pointId: 1, pointName: 'CH₄浓度-1号井', operator: '>', threshold: 20, unit: '%LEL', level: 'critical', enabled: true, notifyMethods: ['web', 'sms'] },
    { id: 2, name: 'H₂S浓度预警', pointId: 2, pointName: 'H₂S浓度-2号井', operator: '>', threshold: 8, unit: 'ppm', level: 'high', enabled: true, notifyMethods: ['web'] },
    { id: 3, name: 'O₂浓度过低', pointId: 4, pointName: 'O₂浓度-1号井', operator: '<', threshold: 19.5, unit: '%', level: 'critical', enabled: true, notifyMethods: ['web', 'email', 'sms'] }
  ]
}

onMounted(() => {
  loadRealtime()
  loadPoints()

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  wsManager = new WebSocketManager(`${protocol}//${window.location.host}/ws/realtime`, {
    onMessage(data) {
      if (data.type === 'alarm') {
        realtimeAlarms.value.unshift(data)
        if (soundEnabled.value) playAlarmSound()
      }
    }
  })
  wsManager.connect()
})

watch(activeTab, (tab) => {
  if (tab === 'history') loadHistory()
  if (tab === 'config') loadConfigs()
})

onBeforeUnmount(() => {
  wsManager?.close()
})
</script>

<style scoped>
.alarm-center {
  min-height: 100%;
}

.tab-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.toolbar-right {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 12px;
}

.alarm-count {
  font-size: 13px;
  color: #909399;
}

.pagination-wrap {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

:deep(.alarm-critical-row) {
  background-color: #fef0f0 !important;
}

:deep(.alarm-high-row) {
  background-color: #fdf6ec !important;
}
</style>
