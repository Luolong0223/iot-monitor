export class WebSocketManager {
  constructor(url, options = {}) {
    this.url = url
    this.reconnectInterval = options.reconnectInterval || 5000
    this.maxReconnectAttempts = options.maxReconnectAttempts || 10
    this.onMessage = options.onMessage || (() => {})
    this.onConnect = options.onConnect || (() => {})
    this.onDisconnect = options.onDisconnect || (() => {})
    this.onError = options.onError || (() => {})

    this.ws = null
    this.reconnectAttempts = 0
    this.reconnectTimer = null
    this.isManualClose = false
    this.heartbeatTimer = null
  }

  connect() {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return
    }

    this.isManualClose = false
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    const fullUrl = this.url.startsWith('ws') ? this.url : `${protocol}//${host}${this.url}`

    try {
      this.ws = new WebSocket(fullUrl)
    } catch (e) {
      console.error('WebSocket creation failed:', e)
      this.scheduleReconnect()
      return
    }

    this.ws.onopen = () => {
      console.log('[WS] Connected to', fullUrl)
      this.reconnectAttempts = 0
      this.startHeartbeat()
      this.onConnect()
    }

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        this.onMessage(data)
      } catch (e) {
        this.onMessage(event.data)
      }
    }

    this.ws.onclose = (event) => {
      console.log('[WS] Disconnected', event.code, event.reason)
      this.stopHeartbeat()
      this.onDisconnect()
      if (!this.isManualClose) {
        this.scheduleReconnect()
      }
    }

    this.ws.onerror = (error) => {
      console.error('[WS] Error:', error)
      this.onError(error)
    }
  }

  send(data) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      const payload = typeof data === 'string' ? data : JSON.stringify(data)
      this.ws.send(payload)
    } else {
      console.warn('[WS] Cannot send, not connected')
    }
  }

  close() {
    this.isManualClose = true
    this.stopHeartbeat()
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }

  startHeartbeat() {
    this.stopHeartbeat()
    this.heartbeatTimer = setInterval(() => {
      this.send({ type: 'ping' })
    }, 30000)
  }

  stopHeartbeat() {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer)
      this.heartbeatTimer = null
    }
  }

  scheduleReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.log('[WS] Max reconnect attempts reached')
      return
    }
    const delay = this.reconnectInterval * Math.pow(1.5, this.reconnectAttempts)
    console.log(`[WS] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts + 1})`)
    this.reconnectTimer = setTimeout(() => {
      this.reconnectAttempts++
      this.connect()
    }, delay)
  }

  get connected() {
    return this.ws && this.ws.readyState === WebSocket.OPEN
  }
}
