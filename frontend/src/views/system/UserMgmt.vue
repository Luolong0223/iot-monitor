<template>
  <div class="user-mgmt">
    <div class="page-header">
      <h2>用户管理</h2>
      <el-button type="primary" @click="showAdd">新增用户</el-button>
    </div>

    <!-- 搜索筛选 -->
    <el-card shadow="never" class="filter-card">
      <el-form :inline="true" :model="filter">
        <el-form-item label="关键词">
          <el-input v-model="filter.keyword" placeholder="用户名/姓名" clearable @keyup.enter="loadData" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="filter.role" clearable placeholder="全部">
            <el-option label="超级管理员" value="superadmin" />
            <el-option label="管理员" value="admin" />
            <el-option label="普通用户" value="user" />
            <el-option label="只读用户" value="readonly" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filter.status" clearable placeholder="全部">
            <el-option label="启用" value="active" />
            <el-option label="禁用" value="disabled" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadData">查询</el-button>
          <el-button @click="resetFilter">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 用户列表 -->
    <el-card shadow="never">
      <el-table :data="users" v-loading="loading" stripe>
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="username" label="用户名" width="120" />
        <el-table-column prop="real_name" label="真实姓名" width="120" />
        <el-table-column prop="phone" label="手机号" width="130" />
        <el-table-column prop="email" label="邮箱" min-width="160" />
        <el-table-column prop="role" label="角色" width="110">
          <template #default="{ row }">
            <el-tag :type="roleTagType(row.role)">{{ roleLabel(row.role) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'danger'" size="small">
              {{ row.status === 'active' ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="last_login" label="最后登录" width="170" />
        <el-table-column label="操作" width="260" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="showEdit(row)">编辑</el-button>
            <el-button size="small" type="warning" @click="resetPwd(row)">重置密码</el-button>
            <el-button size="small" :type="row.status === 'active' ? 'danger' : 'success'" @click="toggleStatus(row)">
              {{ row.status === 'active' ? '禁用' : '启用' }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="filter.page"
          v-model:page-size="filter.page_size"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @current-change="loadData"
          @size-change="loadData"
        />
      </div>
    </el-card>

    <!-- 新增/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑用户' : '新增用户'" width="500px">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" :disabled="isEdit" />
        </el-form-item>
        <el-form-item v-if="!isEdit" label="密码" prop="password">
          <el-input v-model="form.password" type="password" show-password />
        </el-form-item>
        <el-form-item label="真实姓名">
          <el-input v-model="form.real_name" />
        </el-form-item>
        <el-form-item label="手机号">
          <el-input v-model="form.phone" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="form.email" />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-select v-model="form.role" style="width:100%">
            <el-option label="超级管理员" value="superadmin" />
            <el-option label="管理员" value="admin" />
            <el-option label="普通用户" value="user" />
            <el-option label="只读用户" value="readonly" />
          </el-select>
        </el-form-item>
        <el-form-item label="绑定层级">
          <el-tree-select
            v-model="form.hierarchy_id"
            :data="hierarchyTree"
            :props="{ label: 'name', value: 'id', children: 'children' }"
            placeholder="选择层级"
            clearable
            check-strictly
            style="width:100%"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm" :loading="submitting">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getUsers, createUser, updateUser, resetPassword } from '@/api/users'
import { getHierarchyTree } from '@/api/hierarchy'

const loading = ref(false)
const submitting = ref(false)
const users = ref([])
const total = ref(0)
const hierarchyTree = ref([])
const dialogVisible = ref(false)
const isEdit = ref(false)
const editId = ref(null)
const formRef = ref(null)

const filter = reactive({ keyword: '', role: '', status: '', page: 1, page_size: 20 })
const form = reactive({ username: '', password: '', real_name: '', phone: '', email: '', role: 'user', hierarchy_id: null })

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }],
}

const roleLabel = (r) => ({ superadmin: '超级管理员', admin: '管理员', user: '普通用户', readonly: '只读用户' }[r] || r)
const roleTagType = (r) => ({ superadmin: 'danger', admin: 'warning', user: '', readonly: 'info' }[r] || '')

const loadData = async () => {
  loading.value = true
  try {
    const res = await getUsers(filter)
    users.value = res.data.data.list
    total.value = res.data.data.total
  } finally { loading.value = false }
}

const loadTree = async () => {
  try {
    const res = await getHierarchyTree()
    hierarchyTree.value = res.data.data
  } catch {}
}

const resetFilter = () => {
  Object.assign(filter, { keyword: '', role: '', status: '', page: 1, page_size: 20 })
  loadData()
}

const showAdd = () => {
  isEdit.value = false
  editId.value = null
  Object.assign(form, { username: '', password: '', real_name: '', phone: '', email: '', role: 'user', hierarchy_id: null })
  dialogVisible.value = true
}

const showEdit = (row) => {
  isEdit.value = true
  editId.value = row.id
  Object.assign(form, { username: row.username, real_name: row.real_name, phone: row.phone, email: row.email, role: row.role, hierarchy_id: row.hierarchy_id })
  dialogVisible.value = true
}

const submitForm = async () => {
  await formRef.value.validate()
  submitting.value = true
  try {
    if (isEdit.value) {
      await updateUser(editId.value, { real_name: form.real_name, phone: form.phone, email: form.email, role: form.role, hierarchy_id: form.hierarchy_id })
      ElMessage.success('修改成功')
    } else {
      await createUser(form)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    loadData()
  } finally { submitting.value = false }
}

const resetPwd = async (row) => {
  await ElMessageBox.confirm(`确定重置用户 ${row.username} 的密码为 IoT@123456？`, '重置密码', { type: 'warning' })
  await resetPassword(row.id)
  ElMessage.success('密码已重置为 IoT@123456')
}

const toggleStatus = async (row) => {
  const action = row.status === 'active' ? '禁用' : '启用'
  await ElMessageBox.confirm(`确定${action}用户 ${row.username}？`, '提示', { type: 'warning' })
  await updateUser(row.id, { status: row.status === 'active' ? 'disabled' : 'active' })
  ElMessage.success(`${action}成功`)
  loadData()
}

onMounted(() => { loadData(); loadTree() })
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.filter-card { margin-bottom: 16px; }
.pagination-wrap { display: flex; justify-content: flex-end; margin-top: 16px; }
</style>
