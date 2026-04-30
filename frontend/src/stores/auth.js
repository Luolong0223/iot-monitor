import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getToken, setToken, removeToken } from '../utils/auth.js'
import { loginApi, logoutApi, getMeApi } from '../api/auth.js'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(getToken() || '')
  const user = ref(null)
  const permissions = ref([])

  const isLoggedIn = computed(() => !!token.value)
  const username = computed(() => user.value?.username || '')
  const displayName = computed(() => user.value?.nickname || user.value?.username || '')

  async function login(credentials) {
    const res = await loginApi(credentials)
    token.value = res.data.token || res.data.access_token
    setToken(token.value)
    await fetchUser()
    return res
  }

  async function fetchUser() {
    try {
      const res = await getMeApi()
      user.value = res.data
      permissions.value = res.data.permissions || []
    } catch (e) {
      console.error('Failed to fetch user info', e)
    }
  }

  async function logout() {
    try {
      await logoutApi()
    } catch (e) {
      // ignore logout errors
    }
    token.value = ''
    user.value = null
    permissions.value = []
    removeToken()
  }

  function hasPermission(perm) {
    return permissions.value.includes('*') || permissions.value.includes(perm)
  }

  return {
    token, user, permissions,
    isLoggedIn, username, displayName,
    login, fetchUser, logout, hasPermission
  }
})
