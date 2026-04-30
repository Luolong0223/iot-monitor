import request from './request.js'

export function getDeviceList(params) {
  return request({ url: '/devices', method: 'get', params })
}

export function getDeviceDetail(id) {
  return request({ url: `/devices/${id}`, method: 'get' })
}

export function createDevice(data) {
  return request({ url: '/devices', method: 'post', data })
}

export function updateDevice(id, data) {
  return request({ url: `/devices/${id}`, method: 'put', data })
}

export function deleteDevice(id) {
  return request({ url: `/devices/${id}`, method: 'delete' })
}

export function importDevices(file) {
  const formData = new FormData()
  formData.append('file', file)
  return request({ url: '/devices/import', method: 'post', data: formData, headers: { 'Content-Type': 'multipart/form-data' } })
}

export function exportDevices(params) {
  return request({ url: '/devices/export', method: 'get', params, responseType: 'blob' })
}
