import request from './request.js'

export function getProtocolList(params) {
  return request({ url: '/protocols', method: 'get', params })
}

export function getProtocolDetail(id) {
  return request({ url: `/protocols/${id}`, method: 'get' })
}

export function createProtocol(data) {
  return request({ url: '/protocols', method: 'post', data })
}

export function updateProtocol(id, data) {
  return request({ url: `/protocols/${id}`, method: 'put', data })
}

export function deleteProtocol(id) {
  return request({ url: `/protocols/${id}`, method: 'delete' })
}

export function testProtocol(id, data) {
  return request({ url: `/protocols/${id}/test`, method: 'post', data })
}

export function importProtocols(file) {
  const formData = new FormData()
  formData.append('file', file)
  return request({ url: '/protocols/import', method: 'post', data: formData, headers: { 'Content-Type': 'multipart/form-data' } })
}

export function exportProtocols(params) {
  return request({ url: '/protocols/export', method: 'get', params, responseType: 'blob' })
}
