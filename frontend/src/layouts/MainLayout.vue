<template>
  <div class="main-layout">
    <aside class="sidebar" :class="{ collapsed: appStore.sidebarCollapsed }">
      <div class="sidebar-header">
        <img src="https://cdn-icons-png.flaticon.com/512/2917/2917995.png" alt="logo" class="logo" />
        <span v-show="!appStore.sidebarCollapsed" class="title">气体监测平台</span>
      </div>
      <el-menu
        :default-active="activeMenu"
        :collapse="appStore.sidebarCollapsed"
        :collapse-transition="false"
        router
        class="sidebar-menu"
        background-color="#001529"
        text-color="#ffffffb3"
        active-text-color="#409eff"
      >
        <el-menu-item index="/dashboard">
          <el-icon><Odometer /></el-icon>
          <span>数据总览</span>
        </el-menu-item>
        <el-menu-item index="/monitor">
          <el-icon><Monitor /></el-icon>
          <span>实时监控</span>
        </el-menu-item>
        <el-menu-item index="/data-screen">
          <el-icon><DataBoard /></el-icon>
          <span>数据大屏</span>
        </el-menu-item>
        <el-menu-item index="/history">
          <el-icon><TrendCharts /></el-icon>
          <span>历史数据</span>
        </el-menu-item>
        <el-menu-item index="/alarms">
          <el-icon><Bell /></el-icon>
          <span>告警中心</span>
        </el-menu-item>
        <el-menu-item index="/reports">
          <el-icon><Document /></el-icon>
          <span>报表中心</span>
        </el-menu-item>

        <el-sub-menu index="system">
          <template #title>
            <el-icon><Setting /></el-icon>
            <span>系统管理</span>
          </template>
          <el-menu-item index="/system/hierarchy">层级管理</el-menu-item>
          <el-menu-item index="/system/devices">设备管理</el-menu-item>
          <el-menu-item index="/system/data-points">数据点管理</el-menu-item>
          <el-menu-item index="/system/protocols">协议管理</el-menu-item>
          <el-menu-item index="/system/users">用户管理</el-menu-item>
          <el-menu-item index="/system/config">系统配置</el-menu-item>
          <el-menu-item index="/system/logs">操作日志</el-menu-item>
        </el-sub-menu>
      </el-menu>
    </aside>

    <div class="main-content">
      <header class="header">
        <div class="header-left">
          <el-icon class="collapse-btn" @click="appStore.toggleSidebar">
            <Fold v-if="!appStore.sidebarCollapsed" />
            <Expand v-else />
          </el-icon>
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item v-if="route.meta.title">{{ route.meta.title }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="header-right">
          <el-badge :value="appStore.unreadAlarmCount" :hidden="appStore.unreadAlarmCount === 0" class="alarm-badge">
            <el-icon class="header-icon" @click="$router.push('/alarms')"><Bell /></el-icon>
          </el-badge>
          <el-dropdown trigger="click" @command="handleCommand">
            <span class="user-info">
              <el-icon><User /></el-icon>
              <span class="username">{{ authStore.displayName }}</span>
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="password">修改密码</el-dropdown-item>
                <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>

      <main class="page-content">
        <router-view />
      </main>
    </div>

    <!-- Change Password Dialog -->
    <el-dialog v-model="pwdDialogVisible" title="修改密码" width="400px">
      <el-form ref="pwdFormRef" :model="pwdForm" :rules="pwdRules" label-width="100px">
        <el-form-item label="旧密码" prop="oldPassword">
          <el-input v-model="pwdForm.oldPassword" type="password" show-password />
        </el-form-item>
        <el-form-item label="新密码" prop="newPassword">
          <el-input v-model="pwdForm.newPassword" type="password" show-password />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirmPassword">
          <el-input v-model="pwdForm.confirmPassword" type="password" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="pwdDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="pwdLoading" @click="submitPassword">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'
import { useAppStore } from '../stores/app.js'
import { changePasswordApi } from '../api/auth.js'
import { WebSocketManager } from '../utils/websocket.js'
import { ElMessage } from 'element-plus'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const appStore = useAppStore()

const activeMenu = computed(() => route.path)

// Password dialog
const pwdDialogVisible = ref(false)
const pwdLoading = ref(false)
const pwdFormRef = ref(null)
const pwdForm = ref({ oldPassword: '', newPassword: '', confirmPassword: '' })

const validateConfirm = (rule, value, callback) => {
  if (value !== pwdForm.value.newPassword) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const pwdRules = {
  oldPassword: [{ required: true, message: '请输入旧密码', trigger: 'blur' }],
  newPassword: [{ required: true, message: '请输入新密码', trigger: 'blur' }, { min: 6, message: '密码长度至少6位', trigger: 'blur' }],
  confirmPassword: [{ required: true, message: '请确认新密码', trigger: 'blur' }, { validator: validateConfirm, trigger: 'blur' }]
}

function handleCommand(cmd) {
  if (cmd === 'logout') {
    authStore.logout().then(() => {
      router.push('/login')
    })
  } else if (cmd === 'password') {
    pwdForm.value = { oldPassword: '', newPassword: '', confirmPassword: '' }
    pwdDialogVisible.value = true
  }
}

async function submitPassword() {
  try {
    await pwdFormRef.value.validate()
  } catch { return }

  pwdLoading.value = true
  try {
    await changePasswordApi({ oldPassword: pwdForm.value.oldPassword, newPassword: pwdForm.value.newPassword })
    ElMessage.success('密码修改成功')
    pwdDialogVisible.value = false
  } catch (e) {
    // error handled by interceptor
  } finally {
    pwdLoading.value = false
  }
}

// WebSocket for real-time alarms
let wsManager = null

onMounted(() => {
  authStore.fetchUser()

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = `${protocol}//${window.location.host}/ws/realtime`
  wsManager = new WebSocketManager(wsUrl, {
    onMessage(data) {
      if (data.type === 'alarm') {
        appStore.addNotification(data)
        appStore.setUnreadAlarmCount(appStore.unreadAlarmCount + 1)
        ElMessage({ type: 'warning', message: `告警: ${data.message || '新告警'}`, duration: 5000 })
      }
    }
  })
  wsManager.connect()
})

onBeforeUnmount(() => {
  if (wsManager) wsManager.close()
})
</script>

<style scoped>
.main-layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

.sidebar {
  width: 220px;
  background: #001529;
  transition: width 0.3s;
  overflow: hidden;
  flex-shrink: 0;
}

.sidebar.collapsed {
  width: 64px;
}

.sidebar-header {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 16px;
  gap: 10px;
  border-bottom: 1px solid #ffffff1a;
}

.logo {
  width: 32px;
  height: 32px;
  flex-shrink: 0;
}

.title {
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  white-space: nowrap;
}

.sidebar-menu {
  border-right: none;
  height: calc(100vh - 60px);
  overflow-y: auto;
}

.sidebar-menu::-webkit-scrollbar {
  width: 0;
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #f0f2f5;
}

.header {
  height: 60px;
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.collapse-btn {
  font-size: 20px;
  cursor: pointer;
  color: #666;
  transition: color 0.2s;
}

.collapse-btn:hover {
  color: #409eff;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 20px;
}

.header-icon {
  font-size: 20px;
  cursor: pointer;
  color: #666;
}

.header-icon:hover {
  color: #409eff;
}

.alarm-badge {
  line-height: 1;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  color: #666;
}

.username {
  max-width: 100px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.page-content {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
}
</style>
