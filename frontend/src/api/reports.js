import request from './request.js'

export function getDailyReport(params) {
  return request({ url: '/reports/daily', method: 'get', params })
}

export function getMonthlyReport(params) {
  return request({ url: '/reports/monthly', method: 'get', params })
}

export function getCustomReport(params) {
  return request({ url: '/reports/custom', method: 'get', params })
}

export function exportReport(params) {
  return request({ url: '/reports/export', method: 'get', params, responseType: 'blob' })
}
