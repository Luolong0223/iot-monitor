import request from './request.js'

export function loginApi(data) {
  return request({ url: '/auth/login', method: 'post', data })
}

export function logoutApi() {
  return request({ url: '/auth/logout', method: 'post' })
}

export function refreshTokenApi() {
  return request({ url: '/auth/refresh', method: 'post' })
}

export function getMeApi() {
  return request({ url: '/auth/me', method: 'get' })
}

export function changePasswordApi(data) {
  return request({ url: '/auth/password', method: 'put', data })
}
