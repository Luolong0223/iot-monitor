<template>
  <div class="datapoint-mgmt">
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <el-input v-model="search" placeholder="搜索数据点..." prefix-icon="Search" clearable style="width: 240px" />
            <el-select v-model="deviceFilter" placeholder="所属设备" clearable filterable style="width: 200px">
              <el-option v-for="d in deviceOptions" :key="d.id" :label="d.name" :value="d.id" />
            </el-select>
            <el-button type="primary" @click="loadData">查询</el-button>
          </div>
          <div class="header-right">
            <el-button type="success" @click="openDialog()">新增数据点</el-button>
            <el-upload :show-file-list="false" accept=".xlsx,.xls" :before-upload="handleImport" style="display: inline-block; margin-left: 8px">
              <el-button>导入</el-button>
            </el-upload>
          </div>
        </div>
      </template>

      <el-table :data="pointList" stripe v-loading="loading" style="width: 100%">
        <el-table-column prop="name" label="数据点名称" min-width="180" />
        <el-table-column prop="identifier" label="标识符" width="160" />
        <el-table-column prop="deviceName" label="所属设备" width="160" />
        <el-table-column prop="dataType" label="数据类型" width="100" />
        <el-table-column prop="unit" label="单位" width="80" />
        <el-table-column prop="采集频率" label="采集频率(秒)" width="110" />
        <el-table-column prop="thresholdHigh" label="上限" width="80" />
        <el-table-column prop="thresholdLow" label="下限" width="80" />
        <el-table-column prop="enabled" label="状态" width="80">
          <template #default="{ row }">
            <el-switch v-model="row.enabled" @change="toggleEnabled(row)" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="openDialog(row)">编辑</el-button>
            <el-button type="danger" link size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[20, 50, 100]"
          layout="total, sizes, prev, pager, next"
          @current-change="loadData"
          @size-change="loadData"
        />
      </div>
    </el-card>

    <!-- Dialog -->
    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑数据点' : '新增数据点'" width="600px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="名称" prop="name">
              <el-input v-model="form.name" placeholder="如 CH₄浓度" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="标识符" prop="identifier">
              <el-input v-model="form.identifier" placeholder="如 ch4_concentration" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="所属设备" prop="deviceId">
              <el-select v-model="form.deviceId" placeholder="选择设备" filterable style="width: 100%">
                <el-option v-for="d in deviceOptions" :key="d.id" :label="d.name" :value="d.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="数据类型" prop="dataType">
              <el-select v-model="form.dataType" style="width: 100%">
                <el-option label="整数 (int)" value="int" />
                <el-option label="浮点数 (float)" value="float" />
                <el-option label="布尔 (bool)" value="bool" />
                <el-option label="字符串 (string)" value="string" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="单位">
              <el-input v-model="form.unit" placeholder="如 ppm" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="采集频率">
              <el-input-number v-model="form.采集频率" :min="1" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="精度">
              <el-input-number v-model="form.precision" :min="0" :max="6" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="告警下限">
              <el-input-number v-model="form.thresholdLow" :precision="2" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="告警上限">
              <el-input-number v-model="form.thresholdHigh" :precision="2" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getDataPointList, createDataPoint, updateDataPoint, deleteDataPoint, importDataPoints } from '../../api/dataPoints.js'
import { getDeviceList } from '../../api/devices.js'
import { ElMessage, ElMessageBox } from 'element-plus'

const search = ref('')
const deviceFilter = ref('')
const loading = ref(false)
const pointList = ref([])
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

const dialogVisible = ref(false)
const saving = ref(false)
const formRef = ref(null)
const form = ref({
  id: null, name: '', identifier: '', deviceId: null, dataType: 'float',
  unit: '', 采集频率: 10, precision: 2, thresholdLow: null, thresholdHigh: null, description: ''
})

const rules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  identifier: [{ required: true, message: '请输入标识符', trigger: 'blur' }],
  deviceId: [{ required: true, message: '请选择设备', trigger: 'change' }],
  dataType: [{ required: true, message: '请选择数据类型', trigger: 'change' }]
}

const deviceOptions = ref([])

async function loadData() {
  loading.value = true
  try {
    const params = { page: page.value, pageSize: pageSize.value }
    if (search.value) params.keyword = search.value
    if (deviceFilter.value) params.deviceId = deviceFilter.value
    const res = await getDataPointList(params)
    pointList.value = res.data?.list || res.data || []
    total.value = res.data?.total || pointList.value.length
    if (!pointList.value.length) {
      pointList.value = generateDemoData()
      total.value = pointList.value.length
    }
  } catch (e) {
    pointList.value = generateDemoData()
    total.value = pointList.value.length
  } finally {
    loading.value = false
  }
}

function generateDemoData() {
  const names = [
    { name: 'CH₄浓度', identifier: 'ch4_concentration', unit: '%LEL', thresholdLow: 0, thresholdHigh: 25 },
    { name: 'H₂S浓度', identifier: 'h2s_concentration', unit: 'ppm', thresholdLow: 0, thresholdHigh: 10 },
    { name: 'CO浓度', identifier: 'co_concentration', unit: 'ppm', thresholdLow: 0, thresholdHigh: 24 },
    { name: 'O₂浓度', identifier: 'o2_concentration', unit: '%', thresholdLow: 19.5, thresholdHigh: 23.5 },
    { name: '温度', identifier: 'temperature', unit: '℃', thresholdLow: 15, thresholdHigh: 35 },
    { name: '压力', identifier: 'pressure', unit: 'kPa', thresholdLow: 80, thresholdHigh: 120 }
  ]
  return Array.from({ length: 18 }, (_, i) => {
    const n = names[i % names.length]
    return {
      id: i + 1,
      name: `${n.name}-${Math.floor(i / 6) + 1}号井`,
      identifier: `${n.identifier}_${Math.floor(i / 6) + 1}`,
      deviceName: ['甲烷传感器A', '硫化氢传感器B', '一氧化碳传感器C'][i % 3],
      dataType: 'float',
      unit: n.unit,
      采集频率: 10,
      thresholdHigh: n.thresholdHigh,
      thresholdLow: n.thresholdLow,
      enabled: i !== 5
    }
  })
}

async function loadDevices() {
  try {
    const res = await getDeviceList({ pageSize: 1000 })
    deviceOptions.value = res.data?.list || res.data || []
  } catch (e) {
    deviceOptions.value = [
      { id: 1, name: '甲烷传感器A' }, { id: 2, name: '硫化氢传感器B' },
      { id: 3, name: '一氧化碳传感器C' }, { id: 4, name: '氧气传感器D' }
    ]
  }
}

function openDialog(row) {
  if (row) {
    form.value = { ...row }
  } else {
    form.value = { id: null, name: '', identifier: '', deviceId: null, dataType: 'float', unit: '', 采集频率: 10, precision: 2, thresholdLow: null, thresholdHigh: null, description: '' }
  }
  dialogVisible.value = true
}

async function handleSave() {
  try { await formRef.value.validate() } catch { return }
  saving.value = true
  try {
    if (form.value.id) {
      await updateDataPoint(form.value.id, form.value)
    } else {
      await createDataPoint(form.value)
    }
    ElMessage.success('保存成功')
    dialogVisible.value = false
    loadData()
  } catch (e) { /* handled */ } finally {
    saving.value = false
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(`确认删除数据点"${row.name}"？`, '提示')
    await deleteDataPoint(row.id)
    ElMessage.success('已删除')
    loadData()
  } catch (e) { /* cancelled */ }
}

async function toggleEnabled(row) {
  try {
    await updateDataPoint(row.id, { enabled: row.enabled })
    ElMessage.success(row.enabled ? '已启用' : '已禁用')
  } catch (e) {
    row.enabled = !row.enabled
  }
}

async function handleImport(file) {
  try {
    await importDataPoints(file)
    ElMessage.success('导入成功')
    loadData()
  } catch (e) { /* handled */ }
  return false
}

onMounted(() => {
  loadData()
  loadDevices()
})
</script>

<style scoped>
.datapoint-mgmt {
  min-height: 100%;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
}

.header-left, .header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.pagination-wrap {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
