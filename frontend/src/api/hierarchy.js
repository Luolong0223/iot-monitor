import request from './request.js'

export function getHierarchyList(params) {
  return request({ url: '/hierarchy', method: 'get', params })
}

export function getHierarchyTree() {
  return request({ url: '/hierarchy/tree', method: 'get' })
}

export function createHierarchy(data) {
  return request({ url: '/hierarchy', method: 'post', data })
}

export function updateHierarchy(id, data) {
  return request({ url: `/hierarchy/${id}`, method: 'put', data })
}

export function deleteHierarchy(id) {
  return request({ url: `/hierarchy/${id}`, method: 'delete' })
}

export function getHierarchyDetail(id) {
  return request({ url: `/hierarchy/${id}`, method: 'get' })
}
