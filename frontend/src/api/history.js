import request from './request.js'

export function queryHistory(params) {
  return request({ url: '/history/query', method: 'get', params })
}

export function exportHistory(params) {
  return request({ url: '/history/export', method: 'get', params, responseType: 'blob' })
}

export function getHistoryStatistics(params) {
  return request({ url: '/history/statistics', method: 'get', params })
}
