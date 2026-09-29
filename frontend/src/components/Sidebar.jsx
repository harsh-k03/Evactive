import { useState } from 'react'
import { api } from '../api'
import { C, fmtTime } from '../theme'

export default function Sidebar({ init, frame, onError }) {
  if (!frame || !init) return <aside className="sidebar" />
  return (
    <aside className="sidebar">
      <Headcount init={init} frame={frame} />
      <Sitrep frame={frame} />
      <PA frame={frame} />
      <Actions init={init} frame={frame} onError={onError} />
      <Ask onError={onError} />
    </aside>
  )
}

function Headcount({ init, frame }) {
  const h = frame.headcount
  const pct = h.total ? Math.round((h.safe / h.total) * 100) : 0
  return (
    <section className="card">
      <div className="card-h">
        <span>Muster / Headcount</span>
        <span className="mono muted">{h.total} on site</span>
      </div>
      <div className="hc-main">
        <div className="hc-big">
          <span className="mono">{h.safe}</span><span className="muted">/{h.total}</span>
          <div className="hc-lbl">accounted at assembly points</div>
        </div>
        <div className="ring" style={{ '--p': pct }}><span className="mono">{pct}%</span></div>
      </div>
      <div className="hc-grid">
        <Stat label="En route" value={h.evacuating} color={C.status.evacuating} />
        <Stat label="At work" value={h.working} color={C.status.working} />
        <Stat label="Trapped" value={h.trapped} color={C.status.trapped} alert={h.trapped > 0} />
        <Stat label="Injured" value={h.injured} color={C.status.injured} alert={h.injured > 0} />
      </div>
      <div className="aps">
        {init.layout.assembly_points.map((ap, i) => {
          const st = frame.aps.find((a) => a.id === ap.id)
          const n = h.by_ap[ap.id] || 0
          return (
            <div key={ap.id} className={`ap-row ${st?.safe ? '' : 'closed'}`}>
              <span className="swatch" style={{ background: C.ap[i % C.ap.length] }} />
              <span className="ap-name">{ap.name}</span>
              <span className="ap-bar"><span style={{ width: `${h.total ? (n / h.total) * 100 : 0}%`, background: C.ap[i % C.ap.length] }} /></span>
              <span className="mono">{st?.safe ? n : 'CLOSED'}</span>
            </div>
          )
        })}
      </div>
      {frame.peak_queue?.n >= 3 && (
        <div className="peakq">
          Worst bottleneck so far: <b>{frame.peak_queue.n} people</b> queued at {frame.peak_queue.label}
          {frame.hotspots?.length ? <span className="live"> · {frame.hotspots.length} queue{frame.hotspots.length > 1 ? 's' : ''} now</span> : null}
        </div>
      )}
    </section>
  )
}

const Stat = ({ label, value, color, alert }) => (
  <div className={`stat ${alert ? 'alert' : ''}`}>
    <span className="mono" style={{ color }}>{value}</span>
    <span className="muted">{label}</span>
  </div>
)

function Sitrep({ frame }) {
  const s = frame.sitrep
  return (
    <section className="card">
      <div className="card-h">
        <span>Situation report</span>
        {s && <Badge llm={s.llm} t={s.t} />}
      </div>
      <p className="sitrep">{s ? s.text : 'No incident. All detectors normal.'}</p>
    </section>
  )
}

function PA({ frame }) {
  const [lang, setLang] = useState('en')
  const p = frame.pa
  return (
    <section className="card">
      <div className="card-h">
        <span>PA announcement</span>
        <div className="seg small">
          <button className={lang === 'en' ? 'on' : ''} onClick={() => setLang('en')}>EN</button>
          <button className={lang === 'hi' ? 'on' : ''} onClick={() => setLang('hi')}>हिं</button>
        </div>
      </div>
      <p className="pa">{p ? p[lang] : 'No announcements.'}</p>
      {p && <Badge llm={p.llm} t={p.t} />}
    </section>
  )
}

const Badge = ({ llm, t }) => (
  <span className={`badge ${llm ? 'llm' : ''}`}>{llm ? 'LLM' : 'template'} · {fmtTime(t)}</span>
)

function Actions({ init, frame, onError }) {
  const [zone, setZone] = useState('')
  const run = (p) => p.catch((e) => onError?.(e.message))
  const open = frame.leaks.filter((l) => !l.isolated)
  return (
    <section className="card">
      <div className="card-h"><span>Operator override</span></div>
      <div className="actions">
        <button className="btn danger" disabled={frame.stage === 3} onClick={() => run(api.evacuate('site'))}>Evacuate entire site</button>
        <div className="row">
          <select value={zone} onChange={(e) => setZone(e.target.value)}>
            <option value="">Evacuate a zone...</option>
            {init.layout.zones.map((z) => (
              <option key={z.id} value={z.id} disabled={frame.evac_zones.includes(z.id)}>{z.name}</option>
            ))}
          </select>
          <button className="btn" disabled={!zone} onClick={() => run(api.evacuate(zone)).then(() => setZone(''))}>Order</button>
        </div>
        <button className="btn" disabled={!open.length} onClick={() => run(api.isolate())}>
          ESD: isolate {open.length ? `${open.length} active leak${open.length > 1 ? 's' : ''}` : 'gas supply'}
        </button>
      </div>
    </section>
  )
}

function Ask({ onError }) {
  const [q, setQ] = useState('')
  const [a, setA] = useState(null)
  const [busy, setBusy] = useState(false)
  const submit = async (e) => {
    e.preventDefault()
    if (!q.trim()) return
    setBusy(true)
    try {
      setA(await api.ask(q))
    } catch (err) {
      onError?.(err.message)
    } finally {
      setBusy(false)
    }
  }
  return (
    <section className="card">
      <div className="card-h"><span>Ask Evactive</span></div>
      <form onSubmit={submit} className="ask">
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="e.g. Which exits are unsafe right now?" />
        <button className="btn" disabled={busy}>{busy ? '...' : 'Ask'}</button>
      </form>
      {a && <pre className="answer">{a.answer}</pre>}
    </section>
  )
}
