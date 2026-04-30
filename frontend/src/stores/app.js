import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAppStore = defineStore('app', () => {
  const sidebarCollapsed = ref(false)
  const loading = ref(false)
  const notifications = ref([])
  const unreadAlarmCount = ref(0)

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  function setLoading(val) {
    loading.value = val
  }

  function addNotification(notification) {
    notifications.value.unshift(notification)
    if (notifications.value.length > 100) {
      notifications.value = notifications.value.slice(0, 100)
    }
  }

  function setUnreadAlarmCount(count) {
    unreadAlarmCount.value = count
  }

  function clearNotifications() {
    notifications.value = []
  }

  return {
    sidebarCollapsed, loading, notifications, unreadAlarmCount,
    toggleSidebar, setLoading, addNotification, setUnreadAlarmCount, clearNotifications
  }
})
