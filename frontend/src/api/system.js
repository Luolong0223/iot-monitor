import request from './request.js'

export function getSystemConfig() {
  return request({ url: '/system/config', method: 'get' })
}

export function updateSystemConfig(data) {
  return request({ url: '/system/config', method: 'put', data })
}

export function getSystemHealth() {
  return request({ url: '/system/health', method: 'get' })
}

export function getOperationLogs(params) {
  return request({ url: '/system/logs', method: 'get', params })
}

export function createBackup() {
  return request({ url: '/system/backup', method: 'post' })
}

export function getSystemStats() {
  return request({ url: '/system/stats', method: 'get' })
}
