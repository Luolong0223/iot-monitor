<template>
  <div class="system-config">
    <h2>系统配置</h2>

    <el-tabs v-model="activeGroup" @tab-change="filterConfigs">
    <el-tab-pane v-for="g in groups" :key="g.key" :label="g.label" :name="g.key" />

    <el-card shadow="never">
      <el-table :data="filteredConfigs" v-loading="loading" stripe>
        <el-table-column prop="config_key" label="配置项" width="250">
          <template #default="{ row }">
            <span style="font-family:monospace;font-weight:600">{{ row.config_key }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="说明" min-width="200" />
        <el-table-column prop="value_type" label="类型" width="80">
          <template #default="{ row }">
            <el-tag size="small" type="info">{{ row.value_type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="当前值" width="250">
          <template #default="{ row }">
            <!-- Boolean -->
            <el-switch v-if="row.value_type === 'boolean'" v-model="row.config_value"
              active-value="true" inactive-value="false" @change="saveConfig(row)" />
            <!-- Number -->
            <el-input-number v-else-if="row.value_type === 'number'" v-model.number="row.config_value"
              :min="0" controls-position="right" style="width:150px" @change="saveConfig(row)" />
            <!-- String / Json -->
            <el-input v-else v-model="row.config_value" @blur="saveConfig(row)" />
          </template>
        </el-table-column>
      </el-table>
    </el-card>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getSystemConfigs, updateSystemConfig } from '@/api/system'

const loading = ref(false)
const configs = ref([])
const activeGroup = ref('all')

const groups = [
  { key: 'all', label: '全部' },
  { key: 'data_receive', label: '数据接收' },
  { key: 'data_processing', label: '数据处理' },
  { key: 'device', label: '设备管理' },
  { key: 'alarm', label: '告警管理' },
  { key: 'backup', label: '备份维护' },
  { key: 'log', label: '日志系统' },
]

const filteredConfigs = computed(() => {
  if (activeGroup.value === 'all') return configs.value
  return configs.value.filter(c => c.config_group === activeGroup.value)
})

const filterConfigs = () => {}  // computed handles it

const loadData = async () => {
  loading.value = true
  try {
    const res = await getSystemConfigs()
    configs.value = res.data.data
  } finally { loading.value = false }
}

const saveConfig = async (row) => {
  try {
    await updateSystemConfig(row.config_key, { config_value: String(row.config_value) })
    ElMessage.success(`${row.config_key} 已保存`)
  } catch {
    ElMessage.error('保存失败')
    loadData()
  }
}

onMounted(loadData)
</script>

<style scoped>
.system-config h2 { margin-bottom: 16px; }
</style>
