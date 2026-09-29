import { useEffect, useRef, useState } from 'react'

const MAX_LOG = 1200

/** Connects to the backend WebSocket and keeps the latest init payload, frame and agent log. */
export function useEvactive() {
  const [init, setInit] = useState(null)
  const [frame, setFrame] = useState(null)
  const [log, setLog] = useState([])
  const [connected, setConnected] = useState(false)
  const frameRef = useRef(null)
  const lastFrameAt = useRef(0)
  const frameGap = useRef(250)
  const layoutRef = useRef(null)

  useEffect(() => {
    let ws
    let stop = false
    let retry

    const connect = () => {
      const proto = location.protocol === 'https:' ? 'wss' : 'ws'
      ws = new WebSocket(`${proto}://${location.host}/ws`)
      ws.onopen = () => setConnected(true)
      ws.onclose = () => {
        setConnected(false)
        if (!stop) retry = setTimeout(connect, 1500)
      }
      ws.onmessage = (ev) => {
        const msg = JSON.parse(ev.data)
        if (msg.type === 'init') {
          layoutRef.current = msg.layout.id
          setInit(msg)
          frameRef.current = msg.frame
          setFrame(msg.frame)
          setLog(msg.log || [])
        } else if (msg.type === 'frame') {
          if (msg.layout && layoutRef.current && msg.layout !== layoutRef.current) return // stale frame
          const now = performance.now()
          if (lastFrameAt.current) frameGap.current = Math.min(600, now - lastFrameAt.current)
          lastFrameAt.current = now
          frameRef.current = msg
          setFrame(msg)
          if (msg.log && msg.log.length) {
            setLog((prev) => {
              const last = prev.length ? prev[prev.length - 1].seq : 0
              const add = msg.log.filter((e) => e.seq > last)
              const next = add.length ? prev.concat(add) : prev
              return next.length > MAX_LOG ? next.slice(-MAX_LOG) : next
            })
          }
        }
      }
    }
    connect()
    return () => {
      stop = true
      clearTimeout(retry)
      ws && ws.close()
    }
  }, [])

  return { init, frame, frameRef, frameGap, log, connected }
}
