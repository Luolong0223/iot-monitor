import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    component: () => import('../layouts/MainLayout.vue'),
    redirect: '/dashboard',
    meta: { requiresAuth: true },
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('../views/Dashboard.vue'),
        meta: { title: '数据总览' }
      },
      {
        path: 'monitor',
        name: 'Monitor',
        component: () => import('../views/Monitor.vue'),
        meta: { title: '实时监控' }
      },
      {
        path: 'data-screen',
        name: 'DataScreen',
        component: () => import('../views/DataScreen.vue'),
        meta: { title: '数据大屏', fullscreen: true }
      },
      {
        path: 'data-point/:id',
        name: 'DataPointDetail',
        component: () => import('../views/DataPointDetail.vue'),
        meta: { title: '数据点详情' }
      },
      {
        path: 'history',
        name: 'HistoryQuery',
        component: () => import('../views/HistoryQuery.vue'),
        meta: { title: '历史数据' }
      },
      {
        path: 'alarms',
        name: 'AlarmCenter',
        component: () => import('../views/AlarmCenter.vue'),
        meta: { title: '告警中心' }
      },
      {
        path: 'reports',
        name: 'ReportCenter',
        component: () => import('../views/ReportCenter.vue'),
        meta: { title: '报表中心' }
      },
      {
        path: 'system/hierarchy',
        name: 'HierarchyMgmt',
        component: () => import('../views/system/HierarchyMgmt.vue'),
        meta: { title: '层级管理' }
      },
      {
        path: 'system/devices',
        name: 'DeviceMgmt',
        component: () => import('../views/system/DeviceMgmt.vue'),
        meta: { title: '设备管理' }
      },
      {
        path: 'system/data-points',
        name: 'DataPointMgmt',
        component: () => import('../views/system/DataPointMgmt.vue'),
        meta: { title: '数据点管理' }
      },
      {
        path: 'system/protocols',
        name: 'ProtocolMgmt',
        component: () => import('../views/system/ProtocolMgmt.vue'),
        meta: { title: '协议管理' }
      },
      {
        path: 'system/users',
        name: 'UserMgmt',
        component: () => import('../views/system/UserMgmt.vue'),
        meta: { title: '用户管理' }
      },
      {
        path: 'system/config',
        name: 'SystemConfig',
        component: () => import('../views/system/SystemConfig.vue'),
        meta: { title: '系统配置' }
      },
      {
        path: 'system/logs',
        name: 'OperationLogs',
        component: () => import('../views/system/OperationLogs.vue'),
        meta: { title: '操作日志' }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()
  if (to.meta.requiresAuth !== false && !authStore.token) {
    next('/login')
  } else if (to.path === '/login' && authStore.token) {
    next('/dashboard')
  } else {
    next()
  }
})

export default router
