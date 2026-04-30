<template>
  <div class="protocol-mgmt">
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <el-input v-model="search" placeholder="搜索协议..." prefix-icon="Search" clearable style="width: 240px" />
            <el-button type="primary" @click="loadData">查询</el-button>
          </div>
          <div class="header-right">
            <el-button type="success" @click="openDialog()">新增协议</el-button>
            <el-upload :show-file-list="false" accept=".xlsx,.xls" :before-upload="handleImport" style="display: inline-block; margin-left: 8px">
              <el-button>导入</el-button>
            </el-upload>
            <el-button @click="handleExport">导出</el-button>
          </div>
        </div>
      </template>

      <el-table :data="protocolList" stripe v-loading="loading" style="width: 100%">
        <el-table-column prop="name" label="协议名称" min-width="150" />
        <el-table-column prop="type" label="协议类型" width="120">
          <template #default="{ row }">
            <el-tag>{{ row.type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
        <el-table-column prop="deviceCount" label="关联设备数" width="110" />
        <el-table-column prop="enabled" label="状态" width="80">
          <template #default="{ row }">
            <el-switch v-model="row.enabled" @change="toggleEnabled(row)" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="openDialog(row)">编辑</el-button>
            <el-button type="success" link size="small" @click="openTestDialog(row)">测试</el-button>
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

    <!-- Edit Dialog -->
    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑协议' : '新增协议'" width="600px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="协议名称" prop="name">
          <el-input v-model="form.name" placeholder="如 Modbus TCP" />
        </el-form-item>
        <el-form-item label="协议类型" prop="type">
          <el-select v-model="form.type" style="width: 100%">
            <el-option label="Modbus TCP" value="Modbus TCP" />
            <el-option label="Modbus RTU" value="Modbus RTU" />
            <el-option label="MQTT" value="MQTT" />
            <el-option label="HTTP/REST" value="HTTP" />
            <el-option label="OPC UA" value="OPC UA" />
            <el-option label="自定义" value="Custom" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="3" />
        </el-form-item>

        <!-- Modbus specific -->
        <template v-if="form.type?.includes('Modbus')">
          <el-divider content-position="left">Modbus 参数</el-divider>
          <el-row :gutter="16">
            <el-col :span="12">
              <el-form-item label="从站地址">
                <el-input-number v-model="form.config.slaveAddress" :min="1" :max="247" style="width: 100%" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="波特率" v-if="form.type === 'Modbus RTU'">
                <el-select v-model="form.config.baudRate" style="width: 100%">
                  <el-option label="9600" :value="9600" />
                  <el-option label="19200" :value="19200" />
                  <el-option label="38400" :value="38400" />
                  <el-option label="115200" :value="115200" />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>
        </template>

        <!-- MQTT specific -->
        <template v-if="form.type === 'MQTT'">
          <el-divider content-position="left">MQTT 参数</el-divider>
          <el-row :gutter="16">
            <el-col :span="12">
              <el-form-item label="Broker地址">
                <el-input v-model="form.config.broker" placeholder="mqtt://broker:1883" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="Topic前缀">
                <el-input v-model="form.config.topicPrefix" placeholder="sensors/" />
              </el-form-item>
            </el-col>
          </el-row>
        </template>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>

    <!-- Test Dialog -->
    <el-dialog v-model="testDialogVisible" title="协议连接测试" width="500px">
      <el-form :model="testForm" label-width="100px">
        <el-form-item label="协议">
          <el-input :value="testForm.protocolName" disabled />
        </el-form-item>
        <el-form-item label="目标地址">
          <el-input v-model="testForm.host" placeholder="如 192.168.1.100" />
        </el-form-item>
        <el-form-item label="端口">
          <el-input-number v-model="testForm.port" :min="1" :max="65535" style="width: 100%" />
        </el-form-item>
      </el-form>
      <div v-if="testResult" class="test-result" :class="testResult.success ? 'success' : 'fail'">
        <el-icon :size="20"><CircleCheckFilled v-if="testResult.success" /><CircleCloseFilled v-else /></el-icon>
        <span>{{ testResult.message }}</span>
      </div>
      <template #footer>
        <el-button @click="testDialogVisible = false">关闭</el-button>
        <el-button type="primary" :loading="testLoading" @click="runTest">开始测试</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getProtocolList, createProtocol, updateProtocol, deleteProtocol, testProtocol, importProtocols, exportProtocols } from '../../api/protocols.js'
import { ElMessage, ElMessageBox } from 'element-plus'

const search = ref('')
const loading = ref(false)
const protocolList = ref([])
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

const dialogVisible = ref(false)
const saving = ref(false)
const formRef = ref(null)
const form = ref({
  id: null, name: '', type: 'Modbus TCP', description: '',
  config: { slaveAddress: 1, baudRate: 9600, broker: '', topicPrefix: '' }
})

const rules = {
  name: [{ required: true, message: '请输入协议名称', trigger: 'blur' }],
  type: [{ required: true, message: '请选择协议类型', trigger: 'change' }]
}

const testDialogVisible = ref(false)
const testLoading = ref(false)
const testForm = ref({ protocolId: null, protocolName: '', host: '', port: 502 })
const testResult = ref(null)

async function loadData() {
  loading.value = true
  try {
    const params = { page: page.value, pageSize: pageSize.value }
    if (search.value) params.keyword = search.value
    const res = await getProtocolList(params)
    protocolList.value = res.data?.list || res.data || []
    total.value = res.data?.total || protocolList.value.length
    if (!protocolList.value.length) {
      protocolList.value = generateDemoData()
      total.value = protocolList.value.length
    }
  } catch (e) {
    protocolList.value = generateDemoData()
    total.value = protocolList.value.length
  } finally {
    loading.value = false
  }
}

function generateDemoData() {
  return [
    { id: 1, name: 'Modbus TCP 传感器协议', type: 'Modbus TCP', description: '用于Modbus TCP设备的数据采集', deviceCount: 45, enabled: true },
    { id: 2, name: 'Modbus RTU 串口协议', type: 'Modbus RTU', description: '用于RS485串口设备', deviceCount: 32, enabled: true },
    { id: 3, name: 'MQTT IoT协议', type: 'MQTT', description: '用于MQTT协议的IoT设备', deviceCount: 28, enabled: true },
    { id: 4, name: 'HTTP REST API', type: 'HTTP', description: '通过HTTP接口采集数据', deviceCount: 15, enabled: false }
  ]
}

function openDialog(row) {
  if (row) {
    form.value = { ...row, config: row.config || { slaveAddress: 1, baudRate: 9600, broker: '', topicPrefix: '' } }
  } else {
    form.value = { id: null, name: '', type: 'Modbus TCP', description: '', config: { slaveAddress: 1, baudRate: 9600, broker: '', topicPrefix: '' } }
  }
  dialogVisible.value = true
}

async function handleSave() {
  try { await formRef.value.validate() } catch { return }
  saving.value = true
  try {
    if (form.value.id) {
      await updateProtocol(form.value.id, form.value)
    } else {
      await createProtocol(form.value)
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
    await ElMessageBox.confirm(`确认删除协议"${row.name}"？`, '提示')
    await deleteProtocol(row.id)
    ElMessage.success('已删除')
    loadData()
  } catch (e) { /* cancelled */ }
}

async function toggleEnabled(row) {
  try {
    await updateProtocol(row.id, { enabled: row.enabled })
    ElMessage.success(row.enabled ? '已启用' : '已禁用')
  } catch (e) {
    row.enabled = !row.enabled
  }
}

function openTestDialog(row) {
  testForm.value = { protocolId: row.id, protocolName: row.name, host: '', port: row.type?.includes('Modbus') ? 502 : 1883 }
  testResult.value = null
  testDialogVisible.value = true
}

async function runTest() {
  testLoading.value = true
  testResult.value = null
  try {
    const res = await testProtocol(testForm.value.protocolId, { host: testForm.value.host, port: testForm.value.port })
    testResult.value = { success: true, message: res.data?.message || '连接测试成功' }
  } catch (e) {
    testResult.value = { success: false, message: '连接测试失败，请检查地址和端口' }
  } finally {
    testLoading.value = false
  }
}

async function handleImport(file) {
  try {
    await importProtocols(file)
    ElMessage.success('导入成功')
    loadData()
  } catch (e) { /* handled */ }
  return false
}

async function handleExport() {
  try {
    const res = await exportProtocols()
    const url = window.URL.createObjectURL(new Blob([res]))
    const a = document.createElement('a')
    a.href = url
    a.download = `协议列表_${new Date().toISOString().slice(0, 10)}.xlsx`
    a.click()
    window.URL.revokeObjectURL(url)
  } catch (e) {
    ElMessage.info('导出功能需要后端支持')
  }
}

onMounted(loadData)
</script>

<style scoped>
.protocol-mgmt {
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

.test-result {
  margin-top: 16px;
  padding: 12px 16px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
}

.test-result.success {
  background: #f0f9eb;
  color: #67c23a;
  border: 1px solid #e1f3d8;
}

.test-result.fail {
  background: #fef0f0;
  color: #f56c6c;
  border: 1px solid #fde2e2;
}
</style>
