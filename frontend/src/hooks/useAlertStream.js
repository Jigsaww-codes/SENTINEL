import { useEffect, useRef, useState } from 'react'

/** Subscribes to /ws/alerts with auto-reconnect. Calls onEvent({type, data}) for each message. */
export default function useAlertStream(onEvent) {
  const [connected, setConnected] = useState(false)
  const handler = useRef(onEvent)
  handler.current = onEvent

  useEffect(() => {
    let ws, timer, closed = false
    const open = () => {
      const proto = location.protocol === 'https:' ? 'wss' : 'ws'
      ws = new WebSocket(`${proto}://${location.host}/ws/alerts`)
      ws.onopen = () => setConnected(true)
      ws.onmessage = (e) => { try { handler.current?.(JSON.parse(e.data)) } catch { /* ignore */ } }
      ws.onclose = () => { setConnected(false); if (!closed) timer = setTimeout(open, 2000) }
    }
    open()
    return () => { closed = true; clearTimeout(timer); ws?.close() }
  }, [])

  return connected
}
