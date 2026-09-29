import { useEffect, useRef, useState } from 'react'
import { C } from '../theme'

const FIRE_COLORS = ['#ff3b1f', '#ff6a00', '#ff9500', '#ffb703']

/**
 * Live plant map on a <canvas>.
 * - static layer (walls, zones, equipment, assembly points) is drawn once per layout/resize
 * - dynamic layer (gas, smoke, fire, routes, people, detectors) is redrawn every animation frame,
 *   with people interpolated between server frames for smooth motion
 */
export default function PlantMap({ init, frameRef, frameGap, layers, tool, onCellClick, focusWorker }) {
  const wrapRef = useRef(null)
  const canvasRef = useRef(null)
  const staticRef = useRef(null)
  const geomRef = useRef({ s: 8, ox: 0, oy: 0 })
  const posRef = useRef(new Map())
  const lastFrame = useRef(null)
  const fieldsRef = useRef({ gas: null, smoke: null, fire: new Set(), burnt: new Set() })
  const hoverRef = useRef(null)
  const [hover, setHover] = useState(null)
  const [size, setSize] = useState({ w: 800, h: 500 })

  const L = init?.layout

  // ---------------------------------------------------------------- resize
  useEffect(() => {
    const ro = new ResizeObserver(([e]) => {
      const { width, height } = e.contentRect
      setSize({ w: Math.max(200, width), h: Math.max(200, height) })
    })
    ro.observe(wrapRef.current)
    return () => ro.disconnect()
  }, [])

  // ---------------------------------------------------------------- static layer
  useEffect(() => {
    if (!L) return
    const dpr = window.devicePixelRatio || 1
    const s = Math.floor(Math.min(size.w / L.width, size.h / L.height) * 100) / 100
    const ox = Math.floor((size.w - s * L.width) / 2)
    const oy = Math.floor((size.h - s * L.height) / 2)
    geomRef.current = { s, ox, oy }

    const cv = canvasRef.current
    cv.width = size.w * dpr
    cv.height = size.h * dpr
    cv.style.width = `${size.w}px`
    cv.style.height = `${size.h}px`

    const off = document.createElement('canvas')
    off.width = cv.width
    off.height = cv.height
    const g = off.getContext('2d')
    g.scale(dpr, dpr)
    g.fillStyle = C.bg
    g.fillRect(0, 0, size.w, size.h)
    g.translate(ox, oy)

    const W = L.width
    for (let i = 0; i < L.cells.length; i++) {
      const t = L.cells[i]
      const x = (i % W) * s
      const y = Math.floor(i / W) * s
      g.fillStyle = [C.yard, C.floor, C.wall, C.door, C.obstacle, C.exit][t]
      g.fillRect(x, y, s + 0.5, s + 0.5)
    }
    // yard grid (every 5 cells = 10 m)
    g.strokeStyle = C.yardGrid
    g.lineWidth = 1
    for (let x = 0; x <= L.width; x += 5) { g.beginPath(); g.moveTo(x * s, 0); g.lineTo(x * s, L.height * s); g.stroke() }
    for (let y = 0; y <= L.height; y += 5) { g.beginPath(); g.moveTo(0, y * s); g.lineTo(L.width * s, y * s); g.stroke() }
    // redraw walls on top of grid
    for (let i = 0; i < L.cells.length; i++) {
      if (L.cells[i] !== 2) continue
      g.fillStyle = C.wall
      g.fillRect((i % W) * s, Math.floor(i / W) * s, s + 0.5, s + 0.5)
    }
    // equipment hatch + labels
    g.save()
    for (const o of L.obstacles) {
      const [x0, y0, x1, y1] = o.rect
      g.strokeStyle = C.obstacleEdge
      g.strokeRect(x0 * s + 0.5, y0 * s + 0.5, (x1 - x0 + 1) * s - 1, (y1 - y0 + 1) * s - 1)
      g.save()
      g.beginPath()
      g.rect(x0 * s, y0 * s, (x1 - x0 + 1) * s, (y1 - y0 + 1) * s)
      g.clip()
      g.strokeStyle = 'rgba(80,100,125,0.25)'
      for (let k = -40; k < 80; k++) {
        g.beginPath()
        g.moveTo(x0 * s + k * s * 0.8, y0 * s)
        g.lineTo(x0 * s + k * s * 0.8 + (y1 - y0 + 1) * s, (y1 + 1) * s)
        g.stroke()
      }
      g.restore()
      if ((x1 - x0) * s > 60) {
        g.fillStyle = '#5d7089'
        g.font = `500 ${Math.max(9, s * 0.9)}px Inter, system-ui, sans-serif`
        g.textAlign = 'center'
        g.textBaseline = 'middle'
        g.fillText(o.name, ((x0 + x1 + 1) / 2) * s, ((y0 + y1 + 1) / 2) * s)
      }
    }
    g.restore()
    // assembly points
    L.assembly_points.forEach((ap, i) => {
      const [x0, y0, x1, y1] = ap.rect
      g.fillStyle = 'rgba(34,197,94,0.08)'
      g.fillRect(x0 * s, y0 * s, (x1 - x0 + 1) * s, (y1 - y0 + 1) * s)
      g.setLineDash([4, 3])
      g.strokeStyle = C.ap[i % C.ap.length]
      g.lineWidth = 1.5
      g.strokeRect(x0 * s, y0 * s, (x1 - x0 + 1) * s, (y1 - y0 + 1) * s)
      g.setLineDash([])
    })
    // zone labels
    g.font = `600 ${Math.max(9, s * 0.85)}px Inter, system-ui, sans-serif`
    g.textAlign = 'center'
    g.textBaseline = 'middle'
    for (const z of L.zones) {
      g.fillStyle = '#8395ad'
      const maxW = (z.rect[2] - z.rect[0] - 1) * s
      g.fillText(z.short || z.name.toUpperCase(), (z.label[0] + 0.5) * s, (z.label[1] + 0.5) * s, maxW)
    }
    staticRef.current = off
    posRef.current = new Map()
  }, [L, size])

  // ---------------------------------------------------------------- render loop
  useEffect(() => {
    if (!L) return
    let raf
    const W = L.width
    const apIndex = Object.fromEntries(L.assembly_points.map((a, i) => [a.id, i]))
    const sensorPos = Object.fromEntries(L.sensors.map((s) => [s.id, s]))

    const draw = (now) => {
      raf = requestAnimationFrame(draw)
      const cv = canvasRef.current
      const st = staticRef.current
      const f = frameRef.current
      if (!cv || !st || !f) return
      if (f.layout && f.layout !== L.id) return // frame for a plant we haven't redrawn yet (just switched)
      const { s, ox, oy } = geomRef.current
      const dpr = window.devicePixelRatio || 1
      const g = cv.getContext('2d')

      // new server frame -> decode fields and retarget people
      if (f !== lastFrame.current) {
        const prevRun = lastFrame.current?.run
        lastFrame.current = f
        const n = L.width * L.height
        const gas = new Float32Array(n)
        const smoke = new Float32Array(n)
        for (const [i, v] of f.gas) gas[i] = v
        for (const [i, v] of f.smoke) smoke[i] = v
        fieldsRef.current = { gas, smoke, fire: new Set(f.fire), burnt: new Set(f.burnt) }
        if (prevRun !== f.run) posRef.current = new Map()
        const pm = posRef.current
        for (const w of f.workers) {
          const p = pm.get(w.id)
          if (!p) pm.set(w.id, { fx: w.x, fy: w.y, tx: w.x, ty: w.y, t0: now })
          else {
            const k = Math.min(1, (now - p.t0) / frameGap.current)
            const cx = p.fx + (p.tx - p.fx) * k
            const cy = p.fy + (p.ty - p.fy) * k
            const jump = Math.abs(w.x - cx) + Math.abs(w.y - cy) > 6
            Object.assign(p, { fx: jump ? w.x : cx, fy: jump ? w.y : cy, tx: w.x, ty: w.y, t0: now })
          }
        }
      }
      const { gas, smoke, fire, burnt } = fieldsRef.current

      g.setTransform(1, 0, 0, 1, 0, 0)
      g.drawImage(st, 0, 0)
      g.setTransform(dpr, 0, 0, dpr, ox * dpr, oy * dpr)

      // zone status outlines
      for (const z of f.zones) {
        if (z.status === 'normal') continue
        const zz = L.zones.find((q) => q.id === z.id)
        if (!zz) continue
        const [x0, y0, x1, y1] = zz.rect
        const pulse = 0.55 + 0.45 * Math.sin(now / 300)
        g.strokeStyle = z.status === 'hazard' ? `rgba(239,68,68,${pulse})` : z.status === 'evacuating' ? `rgba(251,146,60,${0.8})` : 'rgba(251,191,36,0.7)'
        g.lineWidth = z.status === 'hazard' ? 2.5 : 1.5
        g.strokeRect(x0 * s + 1, y0 * s + 1, (x1 - x0 + 1) * s - 2, (y1 - y0 + 1) * s - 2)
      }

      // gas & smoke fields
      if (gas && (layers.gas || layers.smoke)) {
        for (let i = 0; i < gas.length; i++) {
          const x = (i % W) * s
          const y = Math.floor(i / W) * s
          const sv = smoke[i]
          if (layers.smoke && sv >= 3) {
            g.fillStyle = `rgba(148,163,184,${Math.min(0.7, sv / 110)})`
            g.fillRect(x, y, s + 0.5, s + 0.5)
          }
          const gv = gas[i]
          if (layers.gas && gv >= 2) {
            const a = Math.min(0.8, 0.12 + gv / 100 * 0.7)
            const col = gv >= 40 ? `rgba(217,70,239,${a})` : gv >= 20 ? `rgba(249,115,22,${a})` : `rgba(250,204,21,${a * 0.8})`
            g.fillStyle = col
            g.fillRect(x, y, s + 0.5, s + 0.5)
          }
        }
      }
      // fire
      for (const i of burnt) {
        g.fillStyle = '#2b1712'
        g.fillRect((i % W) * s, Math.floor(i / W) * s, s + 0.5, s + 0.5)
      }
      for (const i of fire) {
        const flick = (i * 7 + Math.floor(now / 120)) % FIRE_COLORS.length
        g.fillStyle = FIRE_COLORS[flick]
        g.fillRect((i % W) * s, Math.floor(i / W) * s, s + 0.5, s + 0.5)
      }

      // exits
      for (const e of f.exits) {
        const ex = L.exits.find((q) => q.id === e.id)
        if (!ex) continue
        const xs = ex.cells.map((c) => c[0])
        const ys = ex.cells.map((c) => c[1])
        const cx = ((Math.min(...xs) + Math.max(...xs) + 1) / 2) * s
        const cy = ((Math.min(...ys) + Math.max(...ys) + 1) / 2) * s
        if (e.blocked) {
          g.strokeStyle = '#ef4444'
          g.lineWidth = 2.5
          const r = s * 1.1
          g.beginPath(); g.moveTo(cx - r, cy - r); g.lineTo(cx + r, cy + r); g.moveTo(cx + r, cy - r); g.lineTo(cx - r, cy + r); g.stroke()
        }
        g.font = `700 ${Math.max(9, s * 0.9)}px 'JetBrains Mono', monospace`
        g.fillStyle = e.blocked ? '#f87171' : '#4ade80'
        g.textAlign = 'center'
        g.textBaseline = 'middle'
        const [odx, ody] = outward(L, ex.cells[0])
        g.fillText(e.id, cx + odx * s * 1.9, cy + ody * s * 1.5)
      }

      // assembly point labels & status
      L.assembly_points.forEach((ap, i) => {
        const st2 = f.aps.find((a) => a.id === ap.id)
        const [x0, y0, x1, y1] = ap.rect
        if (st2 && !st2.safe) {
          g.fillStyle = `rgba(239,68,68,${0.18 + 0.1 * Math.sin(now / 250)})`
          g.fillRect(x0 * s, y0 * s, (x1 - x0 + 1) * s, (y1 - y0 + 1) * s)
        }
        g.font = `700 ${Math.max(9, s * 0.9)}px Inter, system-ui, sans-serif`
        g.fillStyle = st2 && !st2.safe ? '#f87171' : C.ap[i % C.ap.length]
        g.textAlign = 'center'
        g.textBaseline = 'bottom'
        const label = `${ap.id}${st2 && !st2.safe ? ' CLOSED' : ''} · ${f.headcount.by_ap[ap.id] || 0}`
        const ly = y0 === 0 || y0 * s < 14 ? (y1 + 1) * s + s * 1.2 : y0 * s - 3
        g.fillText(label, ((x0 + x1 + 1) / 2) * s, ly)
      })

      // routes
      if (layers.routes) {
        g.lineWidth = Math.max(1, s * 0.18)
        g.lineJoin = 'round'
        for (const [wid, path] of Object.entries(f.paths)) {
          if (path.length < 2) continue
          const w = f.workers.find((q) => q.id === wid)
          const col = C.ap[apIndex[w?.ap] ?? 0]
          const focus = focusWorker && focusWorker === wid
          g.strokeStyle = focus ? '#ffffff' : col
          g.globalAlpha = focus ? 1 : 0.45
          g.lineWidth = focus ? Math.max(2, s * 0.35) : Math.max(1, s * 0.18)
          g.beginPath()
          const p0 = posRef.current.get(wid)
          g.moveTo(((p0 ? p0.tx : path[0][0]) + 0.5) * s, ((p0 ? p0.ty : path[0][1]) + 0.5) * s)
          for (let k = 1; k < path.length; k++) g.lineTo((path[k][0] + 0.5) * s, (path[k][1] + 0.5) * s)
          g.stroke()
        }
        g.globalAlpha = 1
      }

      // leaks
      for (const lk of f.leaks) {
        const cx = (lk.x + 0.5) * s
        const cy = (lk.y + 0.5) * s
        const r = s * (1.2 + 0.5 * ((now / 400) % 1))
        g.strokeStyle = lk.isolated ? 'rgba(148,163,184,0.8)' : 'rgba(217,70,239,0.95)'
        g.lineWidth = 1.5
        g.beginPath(); g.arc(cx, cy, r, 0, Math.PI * 2); g.stroke()
        g.fillStyle = lk.isolated ? '#94a3b8' : '#e879f9'
        g.beginPath(); g.arc(cx, cy, s * 0.45, 0, Math.PI * 2); g.fill()
      }

      // detectors
      if (layers.sensors) {
        for (const sn of f.sensors) {
          const d = sensorPos[sn.id]
          if (!d) continue
          const cx = (d.pos[0] + 0.5) * s
          const cy = (d.pos[1] + 0.5) * s
          const r = Math.max(3, s * 0.55)
          const col = C.sensor[sn.state] || C.sensor.normal
          if (sn.state !== 'normal') {
            g.fillStyle = sn.state === 'A1' ? 'rgba(245,158,11,0.25)' : 'rgba(239,68,68,0.3)'
            g.beginPath(); g.arc(cx, cy, r * (2 + Math.sin(now / 150)), 0, Math.PI * 2); g.fill()
          }
          g.fillStyle = col
          g.strokeStyle = '#0b1016'
          g.lineWidth = 1
          g.beginPath()
          if (d.type === 'gas') { g.moveTo(cx, cy - r); g.lineTo(cx + r, cy); g.lineTo(cx, cy + r); g.lineTo(cx - r, cy); g.closePath() }
          else if (d.type === 'flame') { g.moveTo(cx, cy - r); g.lineTo(cx + r, cy + r * 0.8); g.lineTo(cx - r, cy + r * 0.8); g.closePath() }
          else g.arc(cx, cy, r * 0.85, 0, Math.PI * 2)
          g.fill(); g.stroke()
        }
      }

      // bottlenecks: where evacuees are stuck in a queue
      if (layers.queues && f.hotspots) {
        for (const h of f.hotspots) {
          const cx = (h.x + 0.5) * s
          const cy = (h.y + 0.5) * s
          const pulse = 0.5 + 0.5 * Math.sin(now / 200)
          g.strokeStyle = `rgba(251,146,60,${0.55 + 0.4 * pulse})`
          g.fillStyle = 'rgba(251,146,60,0.12)'
          g.lineWidth = 2
          g.beginPath(); g.arc(cx, cy, s * (2.4 + 0.4 * pulse), 0, Math.PI * 2); g.fill(); g.stroke()
          g.font = `700 ${Math.max(10, s * 0.95)}px Inter, system-ui, sans-serif`
          g.textAlign = 'center'
          g.textBaseline = 'bottom'
          g.fillStyle = '#fdba74'
          g.fillText(`queue ${h.n}`, cx, cy - s * 2.6)
        }
      }

      // people
      const pm = posRef.current
      const rr = Math.max(2.5, s * 0.42)
      for (const w of f.workers) {
        const p = pm.get(w.id)
        if (!p) continue
        const k = Math.min(1, (now - p.t0) / frameGap.current)
        const x = (p.fx + (p.tx - p.fx) * k + 0.5) * s
        const y = (p.fy + (p.ty - p.fy) * k + 0.5) * s
        const col = C.status[w.s] || '#fff'
        if (w.s === 'trapped' || w.s === 'injured') {
          g.fillStyle = `rgba(239,68,68,${0.25 + 0.2 * Math.sin(now / 150)})`
          g.beginPath(); g.arc(x, y, rr * 2.6, 0, Math.PI * 2); g.fill()
        }
        g.fillStyle = col
        g.strokeStyle = focusWorker === w.id ? '#fff' : '#05080b'
        g.lineWidth = focusWorker === w.id ? 2 : 1
        g.beginPath(); g.arc(x, y, rr, 0, Math.PI * 2); g.fill(); g.stroke()
        if (w.kind === 'visitor' || w.kind === 'contractor') {
          g.fillStyle = '#05080b'
          g.beginPath(); g.arc(x, y, rr * 0.35, 0, Math.PI * 2); g.fill()
        }
      }

      // tool hover
      if (hoverRef.current && tool !== 'inspect') {
        const { x, y } = hoverRef.current
        g.strokeStyle = tool === 'fire' ? '#ff6a00' : '#e879f9'
        g.lineWidth = 2
        g.strokeRect(x * s, y * s, s, s)
      }

      // wind arrow
      const wd = f.wind
      g.setTransform(dpr, 0, 0, dpr, 0, 0)
      const ax = size.w - 46
      const ay = 46
      g.fillStyle = 'rgba(10,15,20,0.8)'
      g.strokeStyle = '#243140'
      g.beginPath(); g.arc(ax, ay, 32, 0, Math.PI * 2); g.fill(); g.stroke()
      g.fillStyle = C.muted
      g.font = '600 9px Inter, system-ui, sans-serif'
      g.textAlign = 'center'
      g.textBaseline = 'middle'
      g.fillText('N', ax, ay - 24)
      if (wd.speed_mps > 0.05) {
        const toward = ((wd.from_deg + 180) * Math.PI) / 180
        const dx = Math.sin(toward)
        const dy = -Math.cos(toward)
        g.strokeStyle = '#7dd3fc'
        g.fillStyle = '#7dd3fc'
        g.lineWidth = 2.5
        g.beginPath(); g.moveTo(ax - dx * 16, ay - dy * 16); g.lineTo(ax + dx * 14, ay + dy * 14); g.stroke()
        const hx = ax + dx * 18
        const hy = ay + dy * 18
        g.beginPath()
        g.moveTo(hx, hy)
        g.lineTo(hx - dx * 8 - dy * 5, hy - dy * 8 + dx * 5)
        g.lineTo(hx - dx * 8 + dy * 5, hy - dy * 8 - dx * 5)
        g.closePath(); g.fill()
      }
      g.fillStyle = C.text
      g.font = "600 10px 'JetBrains Mono', monospace"
      g.fillText(`${wd.speed_mps.toFixed(1)} m/s`, ax, ay + 44)
    }
    raf = requestAnimationFrame(draw)
    return () => cancelAnimationFrame(raf)
  }, [L, layers, tool, focusWorker, size])

  // ---------------------------------------------------------------- interaction
  const cellAt = (e) => {
    const r = canvasRef.current.getBoundingClientRect()
    const { s, ox, oy } = geomRef.current
    const x = Math.floor((e.clientX - r.left - ox) / s)
    const y = Math.floor((e.clientY - r.top - oy) / s)
    if (!L || x < 0 || y < 0 || x >= L.width || y >= L.height) return null
    return { x, y, px: e.clientX - r.left, py: e.clientY - r.top }
  }
  const onMove = (e) => {
    const c = cellAt(e)
    hoverRef.current = c
    setHover(c)
  }
  const onClick = (e) => {
    const c = cellAt(e)
    if (c) onCellClick?.(c.x, c.y)
  }

  const tip = hover && L && frameRef.current ? describe(hover, L, frameRef.current, fieldsRef.current) : null

  return (
    <div ref={wrapRef} className={`map-wrap tool-${tool}`}>
      <canvas ref={canvasRef} onMouseMove={onMove} onMouseLeave={() => { hoverRef.current = null; setHover(null) }} onClick={onClick} />
      {tip && (
        <div className="map-tip" style={{ left: Math.min(hover.px + 14, size.w - 240), top: Math.min(hover.py + 14, size.h - 120) }}>
          {tip.map((t, i) => <div key={i} className={i === 0 ? 'tip-head' : ''}>{t}</div>)}
        </div>
      )}
    </div>
  )
}

// direction from an exit cell toward the open yard (for label placement)
function outward(L, [x, y]) {
  for (const [dx, dy] of [[0, -1], [0, 1], [-1, 0], [1, 0]]) {
    const nx = x + dx
    const ny = y + dy
    if (nx >= 0 && ny >= 0 && nx < L.width && ny < L.height && L.cells[ny * L.width + nx] === 0) return [dx, dy]
  }
  return [0, -1]
}

function describe(h, L, f, fields) {
  const i = h.y * L.width + h.x
  const z = L.zones.find((q) => {
    const [x0, y0, x1, y1] = q.rect
    return h.x >= x0 && h.x <= x1 && h.y >= y0 && h.y <= y1
  })
  const out = []
  const w = f.workers.find((q) => q.x === h.x && q.y === h.y)
  const sn = L.sensors.find((q) => q.pos[0] === h.x && q.pos[1] === h.y)
  if (w) {
    out.push(`${w.id} · ${w.name}`)
    out.push(`${w.role} (${w.kind})`)
    out.push(`Status: ${w.s}${w.ap ? ' → ' + w.ap : ''}`)
  } else if (sn) {
    const live = f.sensors.find((q) => q.id === sn.id)
    const unit = sn.type === 'gas' ? '% LEL' : sn.type === 'smoke' ? '% obscuration' : ' flame cells'
    const kind = sn.type === 'gas' ? `Gas detector · ${sn.gas}` : sn.type === 'flame' ? 'UV/IR flame detector' : 'Smoke detector'
    out.push(`${sn.id} · ${kind}`)
    out.push(`Reading: ${live?.v ?? '-'}${unit} · ${live?.state}`)
  } else {
    out.push(z ? z.name : 'Open yard')
  }
  out.push(`Cell (${h.x}, ${h.y})`)
  const gv = fields.gas?.[i] || 0
  const sv = fields.smoke?.[i] || 0
  if (fields.fire.has(i)) out.push('BURNING')
  if (gv >= 2) out.push(`Gas: ${Math.min(100, gv).toFixed(0)}% LEL`)
  if (sv >= 3) out.push(`Smoke: ${sv.toFixed(0)}%`)
  return out
}
