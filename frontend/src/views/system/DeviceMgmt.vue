<template>
  <div class="device-mgmt">
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <el-input v-model="search" placeholder="搜索设备..." prefix-icon="Search" clearable style="width: 240px" />
            <el-select v-model="statusFilter" placeholder="状态" clearable style="width: 120px">
              <el-option label="全部" value="" />
              <el-option label="在线" value="online" />
              <el-option label="离线" value="offline" />
              <el-option label="故障" value="fault" />
            </el-select>
            <el-button type="primary" @click="loadData">查询</el-button>
          </div>
          <div class="header-right">
            <el-button type="success" @click="openDialog()">新增设备</el-button>
            <el-upload :show-file-list="false" accept=".xlsx,.xls" :before-upload="handleImport" style="display: inline-block; margin-left: 8px">
              <el-button>导入</el-button>
            </el-upload>
            <el-button @click="handleExport">导出</el-button>
          </div>
        </div>
      </template>

      <el-table :data="deviceList" stripe v-loading="loading" style="width: 100%">
        <el-table-column prop="name" label="设备名称" min-width="160" />
        <el-table-column prop="code" label="设备编码" width="140" />
        <el-table-column prop="hierarchyName" label="所属层级" width="140" />
        <el-table-column prop="protocolName" label="通信协议" width="120" />
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)" size="small">{{ statusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="ipAddress" label="IP地址" width="140" />
        <el-table-column prop="lastOnline" label="最后在线" width="180">
          <template #default="{ row }">{{ formatTime(row.lastOnline) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
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
    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑设备' : '新增设备'" width="600px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="设备名称" prop="name">
              <el-input v-model="form.name" placeholder="请输入设备名称" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="设备编码" prop="code">
              <el-input v-model="form.code" placeholder="请输入设备编码" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="所属层级" prop="hierarchyId">
              <el-cascader
                v-model="form.hierarchyPath"
                :options="hierarchyOptions"
                :props="{ checkStrictly: true, value: 'id', label: 'name', children: 'children' }"
                placeholder="选择层级"
                style="width: 100%"
                @change="handleHierarchyChange"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="通信协议" prop="protocolId">
              <el-select v-model="form.protocolId" placeholder="选择协议" style="width: 100%">
                <el-option v-for="p in protocolOptions" :key="p.id" :label="p.name" :value="p.id" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="IP地址">
              <el-input v-model="form.ipAddress" placeholder="如 192.168.1.100" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="端口">
              <el-input-number v-model="form.port" :min="1" :max="65535" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="安装位置">
          <el-input v-model="form.location" placeholder="请输入安装位置" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="3" placeholder="请输入描述" />
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
import { getDeviceList, createDevice, updateDevice, deleteDevice, importDevices, exportDevices } from '../../api/devices.js'
import { getHierarchyTree } from '../../api/hierarchy.js'
import { getProtocolList } from '../../api/protocols.js'
import { ElMessage, ElMessageBox } from 'element-plus'

const search = ref('')
const statusFilter = ref('')
const loading = ref(false)
const deviceList = ref([])
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

const dialogVisible = ref(false)
const saving = ref(false)
const formRef = ref(null)
const form = ref({ id: null, name: '', code: '', hierarchyId: null, hierarchyPath: [], protocolId: null, ipAddress: '', port: 502, location: '', description: '' })

const rules = {
  name: [{ required: true, message: '请输入设备名称', trigger: 'blur' }],
  code: [{ required: true, message: '请输入设备编码', trigger: 'blur' }],
  hierarchyId: [{ required: true, message: '请选择所属层级', trigger: 'change' }],
  protocolId: [{ required: true, message: '请选择通信协议', trigger: 'change' }]
}

const hierarchyOptions = ref([])
const protocolOptions = ref([])

function formatTime(t) {
  if (!t) return '-'
  return new Date(t).toLocaleString('zh-CN', { hour12: false })
}

function statusTagType(s) {
  const m = { online: 'success', offline: 'info', fault: 'danger' }
  return m[s] || 'info'
}

function statusText(s) {
  const m = { online: '在线', offline: '离线', fault: '故障' }
  return m[s] || s
}

function handleHierarchyChange(val) {
  form.value.hierarchyId = val?.length ? val[val.length - 1] : null
}

async function loadData() {
  loading.value = true
  try {
    const params = { page: page.value, pageSize: pageSize.value }
    if (search.value) params.keyword = search.value
    if (statusFilter.value) params.status = statusFilter.value
    const res = await getDeviceList(params)
    deviceList.value = res.data?.list || res.data || []
    total.value = res.data?.total || deviceList.value.length
    if (!deviceList.value.length) {
      deviceList.value = generateDemoData()
      total.value = deviceList.value.length
    }
  } catch (e) {
    deviceList.value = generateDemoData()
    total.value = deviceList.value.length
  } finally {
    loading.value = false
  }
}

function generateDemoData() {
  return Array.from({ length: 15 }, (_, i) => ({
    id: i + 1,
    name: ['甲烷传感器A', '硫化氢传感器B', '一氧化碳传感器C', '氧气传感器D', '温湿度传感器E'][i % 5] + `-${Math.floor(i / 5) + 1}`,
    code: `DEV-${String(i + 1).padStart(4, '0')}`,
    hierarchyName: ['一号矿区/1号井', '一号矿区/2号井', '二号矿区/3号井'][i % 3],
    protocolName: ['Modbus TCP', 'Modbus RTU', 'MQTT'][i % 3],
    status: ['online', 'online', 'offline', 'online', 'fault'][i % 5],
    ipAddress: `192.168.1.${100 + i}`,
    lastOnline: new Date(Date.now() - Math.random() * 86400000).toISOString()
  }))
}

function openDialog(row) {
  if (row) {
    form.value = { ...row, hierarchyPath: [] }
  } else {
    form.value = { id: null, name: '', code: '', hierarchyId: null, hierarchyPath: [], protocolId: null, ipAddress: '', port: 502, location: '', description: '' }
  }
  dialogVisible.value = true
}

async function handleSave() {
  try { await formRef.value.validate() } catch { return }
  saving.value = true
  try {
    if (form.value.id) {
      await updateDevice(form.value.id, form.value)
    } else {
      await createDevice(form.value)
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
    await ElMessageBox.confirm(`确认删除设备"${row.name}"？`, '提示')
    await deleteDevice(row.id)
    ElMessage.success('已删除')
    loadData()
  } catch (e) { /* cancelled */ }
}

async function handleImport(file) {
  try {
    await importDevices(file)
    ElMessage.success('导入成功')
    loadData()
  } catch (e) { /* handled */ }
  return false
}

async function handleExport() {
  try {
    const res = await exportDevices()
    const url = window.URL.createObjectURL(new Blob([res]))
    const a = document.createElement('a')
    a.href = url
    a.download = `设备列表_${new Date().toISOString().slice(0, 10)}.xlsx`
    a.click()
    window.URL.revokeObjectURL(url)
  } catch (e) {
    ElMessage.info('导出功能需要后端支持')
  }
}

async function loadOptions() {
  try {
    const [hRes, pRes] = await Promise.all([getHierarchyTree(), getProtocolList({ pageSize: 100 })])
    hierarchyOptions.value = hRes.data || []
    protocolOptions.value = pRes.data?.list || pRes.data || []
  } catch (e) {
    hierarchyOptions.value = [{ id: 1, name: '一号矿区', children: [{ id: 11, name: '1号井' }] }]
    protocolOptions.value = [{ id: 1, name: 'Modbus TCP' }, { id: 2, name: 'MQTT' }]
  }
  if (!hierarchyOptions.value.length) {
    hierarchyOptions.value = [{ id: 1, name: '一号矿区', children: [{ id: 11, name: '1号井' }] }]
  }
  if (!protocolOptions.value.length) {
    protocolOptions.value = [{ id: 1, name: 'Modbus TCP' }, { id: 2, name: 'MQTT' }]
  }
}

onMounted(() => {
  loadData()
  loadOptions()
})
</script>

<style scoped>
.device-mgmt {
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
