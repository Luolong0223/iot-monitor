import request from './request.js'

export function getRealtimeOverview() {
  return request({ url: '/realtime/overview', method: 'get' })
}

export function getRealtimePointData(pointId) {
  return request({ url: `/realtime/points/${pointId}`, method: 'get' })
}

export function getRealtimeHierarchyData(hierarchyId) {
  return request({ url: `/realtime/hierarchy/${hierarchyId}`, method: 'get' })
}

export function getRealtimeAllPoints() {
  return request({ url: '/realtime/points', method: 'get' })
}
