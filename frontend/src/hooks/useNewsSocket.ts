import { useEffect, useRef, useCallback } from 'react'

type EventHandler = (data: unknown) => void

export function useNewsSocket(handlers: Record<string, EventHandler>) {
  const wsRef = useRef<WebSocket | null>(null)
  const handlersRef = useRef(handlers)
  handlersRef.current = handlers

  const connect = useCallback(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/api/ws/news`

    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data)
        const handler = handlersRef.current[msg.type]
        if (handler) handler(msg.data)
      } catch {
        // ignore parse errors
      }
    }

    ws.onclose = () => {
      setTimeout(connect, 5000)
    }

    ws.onerror = () => {
      ws.close()
    }
  }, [])

  useEffect(() => {
    connect()
    return () => {
      wsRef.current?.close()
    }
  }, [connect])
}
