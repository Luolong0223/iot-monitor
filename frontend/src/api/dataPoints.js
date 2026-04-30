import request from './request.js'

export function getDataPointList(params) {
  return request({ url: '/data-points', method: 'get', params })
}

export function getDataPointDetail(id) {
  return request({ url: `/data-points/${id}`, method: 'get' })
}

export function createDataPoint(data) {
  return request({ url: '/data-points', method: 'post', data })
}

export function updateDataPoint(id, data) {
  return request({ url: `/data-points/${id}`, method: 'put', data })
}

export function deleteDataPoint(id) {
  return request({ url: `/data-points/${id}`, method: 'delete' })
}

export function getDataPointItems(id, params) {
  return request({ url: `/data-points/${id}/items`, method: 'get', params })
}

export function importDataPoints(file) {
  const formData = new FormData()
  formData.append('file', file)
  return request({ url: '/data-points/import', method: 'post', data: formData, headers: { 'Content-Type': 'multipart/form-data' } })
}
