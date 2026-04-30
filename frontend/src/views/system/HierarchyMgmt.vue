<template>
  <div class="hierarchy-mgmt">
    <el-row :gutter="20">
      <!-- Tree Panel -->
      <el-col :xs="24" :md="8">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>层级结构</span>
              <el-button type="primary" size="small" @click="openDialog(null, 'root')">新增根节点</el-button>
            </div>
          </template>
          <el-tree
            ref="treeRef"
            :data="treeData"
            :props="{ label: 'name', children: 'children' }"
            node-key="id"
            highlight-current
            default-expand-all
            :expand-on-click-node="false"
            @node-click="handleNodeClick"
          >
            <template #default="{ node, data }">
              <div class="tree-node">
                <span class="tree-label">{{ node.label }}</span>
                <span class="tree-actions">
                  <el-button type="primary" link size="small" @click.stop="openDialog(data, 'child')">+</el-button>
                  <el-button type="primary" link size="small" @click.stop="openDialog(data, 'edit')">✎</el-button>
                  <el-button type="danger" link size="small" @click.stop="handleDelete(data)">×</el-button>
                </span>
              </div>
            </template>
          </el-tree>
        </el-card>
      </el-col>

      <!-- Detail Panel -->
      <el-col :xs="24" :md="16">
        <el-card shadow="hover">
          <template #header><span>节点详情</span></template>
          <div v-if="selectedNode">
            <el-descriptions :column="2" border>
              <el-descriptions-item label="名称">{{ selectedNode.name }}</el-descriptions-item>
              <el-descriptions-item label="编码">{{ selectedNode.code || '--' }}</el-descriptions-item>
              <el-descriptions-item label="类型">{{ selectedNode.type || '--' }}</el-descriptions-item>
              <el-descriptions-item label="排序">{{ selectedNode.sort ?? 0 }}</el-descriptions-item>
              <el-descriptions-item label="描述" :span="2">{{ selectedNode.description || '--' }}</el-descriptions-item>
              <el-descriptions-item label="创建时间">{{ formatTime(selectedNode.createdAt) }}</el-descriptions-item>
              <el-descriptions-item label="更新时间">{{ formatTime(selectedNode.updatedAt) }}</el-descriptions-item>
            </el-descriptions>

            <h4 style="margin: 20px 0 12px">子节点列表</h4>
            <el-table :data="selectedNode.children || []" stripe style="width: 100%">
              <el-table-column prop="name" label="名称" />
              <el-table-column prop="code" label="编码" width="120" />
              <el-table-column prop="type" label="类型" width="100" />
              <el-table-column label="操作" width="140">
                <template #default="{ row }">
                  <el-button type="primary" link size="small" @click="openDialog(row, 'edit')">编辑</el-button>
                  <el-button type="danger" link size="small" @click="handleDelete(row)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
          <el-empty v-else description="请在左侧选择节点" />
        </el-card>
      </el-col>
    </el-row>

    <!-- Dialog -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="500px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入名称" />
        </el-form-item>
        <el-form-item label="编码" prop="code">
          <el-input v-model="form.code" placeholder="请输入编码" />
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="form.type" placeholder="选择类型" style="width: 100%">
            <el-option label="区域" value="area" />
            <el-option label="矿区" value="mine" />
            <el-option label="矿井" value="well" />
            <el-option label="工作面" value="face" />
            <el-option label="设备组" value="device_group" />
          </el-select>
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="form.sort" :min="0" style="width: 100%" />
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
import { getHierarchyTree, createHierarchy, updateHierarchy, deleteHierarchy } from '../api/hierarchy.js'
import { ElMessage, ElMessageBox } from 'element-plus'

const treeRef = ref(null)
const treeData = ref([])
const selectedNode = ref(null)

const dialogVisible = ref(false)
const dialogTitle = ref('')
const saving = ref(false)
const formRef = ref(null)
const form = ref({ id: null, parentId: null, name: '', code: '', type: 'well', sort: 0, description: '' })

const rules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }]
}

function formatTime(t) {
  if (!t) return '-'
  return new Date(t).toLocaleString('zh-CN', { hour12: false })
}

function handleNodeClick(data) {
  selectedNode.value = data
}

function openDialog(data, mode) {
  if (mode === 'edit' && data) {
    dialogTitle.value = '编辑节点'
    form.value = { ...data }
  } else if (mode === 'child' && data) {
    dialogTitle.value = '新增子节点'
    form.value = { id: null, parentId: data.id, name: '', code: '', type: 'well', sort: 0, description: '' }
  } else {
    dialogTitle.value = '新增根节点'
    form.value = { id: null, parentId: null, name: '', code: '', type: 'area', sort: 0, description: '' }
  }
  dialogVisible.value = true
}

async function handleSave() {
  try { await formRef.value.validate() } catch { return }

  saving.value = true
  try {
    if (form.value.id) {
      await updateHierarchy(form.value.id, form.value)
    } else {
      await createHierarchy(form.value)
    }
    ElMessage.success('保存成功')
    dialogVisible.value = false
    loadTree()
  } catch (e) { /* handled */ } finally {
    saving.value = false
  }
}

async function handleDelete(data) {
  try {
    await ElMessageBox.confirm(`确认删除节点"${data.name}"？子节点将同时删除。`, '警告', { type: 'warning' })
    await deleteHierarchy(data.id)
    ElMessage.success('已删除')
    if (selectedNode.value?.id === data.id) selectedNode.value = null
    loadTree()
  } catch (e) { /* cancelled */ }
}

async function loadTree() {
  try {
    const res = await getHierarchyTree()
    treeData.value = res.data || []
    if (!treeData.value.length) {
      treeData.value = generateDemoTree()
    }
  } catch (e) {
    treeData.value = generateDemoTree()
  }
}

function generateDemoTree() {
  return [
    {
      id: 1, name: '华北矿区', code: 'HB', type: 'area', sort: 1, description: '华北区域矿区', createdAt: '2024-01-01T00:00:00', updatedAt: '2024-01-15T10:00:00',
      children: [
        {
          id: 11, name: '一号矿区', code: 'HB-01', type: 'mine', sort: 1, description: '一号矿区', createdAt: '2024-01-02T00:00:00', updatedAt: '2024-01-15T10:00:00',
          children: [
            { id: 111, name: '1号井', code: 'HB-01-01', type: 'well', sort: 1, description: '', createdAt: '2024-01-03T00:00:00', updatedAt: '2024-01-15T10:00:00', children: [] },
            { id: 112, name: '2号井', code: 'HB-01-02', type: 'well', sort: 2, description: '', createdAt: '2024-01-03T00:00:00', updatedAt: '2024-01-15T10:00:00', children: [] }
          ]
        },
        {
          id: 12, name: '二号矿区', code: 'HB-02', type: 'mine', sort: 2, description: '二号矿区', createdAt: '2024-01-02T00:00:00', updatedAt: '2024-01-15T10:00:00',
          children: [
            { id: 121, name: '3号井', code: 'HB-02-01', type: 'well', sort: 1, description: '', createdAt: '2024-01-03T00:00:00', updatedAt: '2024-01-15T10:00:00', children: [] }
          ]
        }
      ]
    }
  ]
}

onMounted(loadTree)
</script>

<style scoped>
.hierarchy-mgmt {
  min-height: 100%;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.tree-node {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding-right: 8px;
}

.tree-label {
  font-size: 14px;
}

.tree-actions {
  display: none;
}

.tree-node:hover .tree-actions {
  display: flex;
  gap: 2px;
}
</style>
