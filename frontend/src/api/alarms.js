import request from './request.js'

export function getAlarmList(params) {
  return request({ url: '/alarms', method: 'get', params })
}

export function getAlarmDetail(id) {
  return request({ url: `/alarms/${id}`, method: 'get' })
}

export function acknowledgeAlarm(id, data) {
  return request({ url: `/alarms/${id}/acknowledge`, method: 'post', data })
}

export function resolveAlarm(id, data) {
  return request({ url: `/alarms/${id}/resolve`, method: 'post', data })
}

export function batchAcknowledgeAlarms(data) {
  return request({ url: '/alarms/batch-acknowledge', method: 'post', data })
}

export function getAlarmConfig(params) {
  return request({ url: '/alarms/config', method: 'get', params })
}

export function updateAlarmConfig(id, data) {
  return request({ url: `/alarms/config/${id}`, method: 'put', data })
}

export function createAlarmConfig(data) {
  return request({ url: '/alarms/config', method: 'post', data })
}

export function deleteAlarmConfig(id) {
  return request({ url: `/alarms/config/${id}`, method: 'delete' })
}

export function getAlarmStats(params) {
  return request({ url: '/alarms/stats', method: 'get', params })
}
