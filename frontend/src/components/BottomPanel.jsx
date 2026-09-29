import { useEffect, useMemo, useRef, useState } from 'react'
import { AGENT_COLORS, C, fmtTime } from '../theme'

const AGENTS = ['Detection', 'Assessment', 'Commander', 'Routing', 'Comms', 'Accountability']

export default function BottomPanel({ init, frame, log, onFocusWorker, focusWorker }) {
  const [tab, setTab] = useState('log')
  return (
    <section className="bottom">
      <div className="tabs">
        <button className={tab === 'log' ? 'on' : ''} onClick={() => setTab('log')}>Agent activity</button>
        <button className={tab === 'det' ? 'on' : ''} onClick={() => setTab('det')}>Detectors</button>
        <button className={tab === 'ppl' ? 'on' : ''} onClick={() => setTab('ppl')}>Personnel</button>
      </div>
      <div className="tab-body">
        {tab === 'log' && <AgentLog log={log} />}
        {tab === 'det' && <Detectors init={init} frame={frame} />}
        {tab === 'ppl' && <Personnel init={init} frame={frame} onFocus={onFocusWorker} focus={focusWorker} />}
      </div>
    </section>
  )
}

function AgentLog({ log }) {
  const [off, setOff] = useState(() => new Set(['Simulator']))
  const [follow, setFollow] = useState(true)
  const ref = useRef(null)
  const rows = useMemo(() => log.filter((e) => !off.has(e.agent)), [log, off])
  useEffect(() => {
    if (follow && ref.current) ref.current.scrollTop = ref.current.scrollHeight
  }, [rows, follow])
  const toggle = (a) => setOff((s) => {
    const n = new Set(s)
    n.has(a) ? n.delete(a) : n.add(a)
    return n
  })
  return (
    <div className="agentlog">
      <div className="chips">
        {[...AGENTS, 'Simulator'].map((a) => (
          <button key={a} className={`chip ${off.has(a) ? 'off' : ''}`} style={{ '--c': AGENT_COLORS[a] }} onClick={() => toggle(a)}>{a}</button>
        ))}
        <label className="follow"><input type="checkbox" checked={follow} onChange={(e) => setFollow(e.target.checked)} /> follow</label>
      </div>
      <div className="log-rows" ref={ref} onScroll={(e) => {
        const el = e.currentTarget
        const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 30
        if (atBottom !== follow) setFollow(atBottom)
      }}>
        {rows.map((e) => (
          <div key={e.seq} className={`log-row lvl-${e.level} kind-${e.kind}`}>
            <span className="mono t">{fmtTime(e.t)}</span>
            <span className="agent" style={{ color: AGENT_COLORS[e.agent] || C.muted }}>{e.agent}</span>
            <span className="msg">
              {e.llm && <span className="badge llm">LLM</span>}
              {e.kind === 'decision' && <span className="badge dec">DECISION</span>}
              {e.msg}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

function Detectors({ init, frame }) {
  const live = Object.fromEntries(frame.sensors.map((s) => [s.id, s]))
  const zname = (x, y) => init.layout.zones.find((z) => {
    const [x0, y0, x1, y1] = z.rect
    return x >= x0 && x <= x1 && y >= y0 && y <= y1
  })?.name || 'Yard'
  const kind = { gas: 'Flammable gas', flame: 'UV/IR flame', smoke: 'Point smoke' }
  const unit = { gas: '% LEL', flame: 'cells', smoke: '% obs' }
  return (
    <table className="tbl">
      <thead><tr><th>ID</th><th>Type</th><th>Medium</th><th>Location</th><th>Reading</th><th>State</th></tr></thead>
      <tbody>
        {init.layout.sensors.map((s) => {
          const l = live[s.id]
          return (
            <tr key={s.id} className={l?.state !== 'normal' ? 'hot' : ''}>
              <td className="mono">{s.id}</td>
              <td>{kind[s.type]}</td>
              <td className="muted">{s.gas || '-'}</td>
              <td>{zname(...s.pos)}</td>
              <td className="mono">{l?.v} {unit[s.type]}</td>
              <td><span className={`state st-${l?.state}`}>{l?.state}</span></td>
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}

function Personnel({ init, frame, onFocus, focus }) {
  const [filter, setFilter] = useState('all')
  const zn = Object.fromEntries(init.layout.zones.map((z) => [z.id, z.name]))
  const order = { trapped: 0, injured: 1, alerted: 2, evacuating: 3, working: 4, safe: 5 }
  const rows = frame.workers
    .filter((w) => filter === 'all' || w.s === filter)
    .sort((a, b) => order[a.s] - order[b.s] || a.id.localeCompare(b.id))
  return (
    <div>
      <div className="chips">
        {['all', 'working', 'alerted', 'evacuating', 'safe', 'trapped', 'injured'].map((s) => (
          <button key={s} className={`chip ${filter === s ? '' : 'off'}`} style={{ '--c': C.status[s] || '#94a3b8' }} onClick={() => setFilter(s)}>{s}</button>
        ))}
      </div>
      <table className="tbl">
        <thead><tr><th>ID</th><th>Name</th><th>Role</th><th>Type</th><th>Work zone</th><th>Status</th><th>Assembly pt</th></tr></thead>
        <tbody>
          {rows.map((w) => (
            <tr key={w.id} className={focus === w.id ? 'sel' : ''} onClick={() => onFocus(focus === w.id ? null : w.id)}>
              <td className="mono">{w.id}</td>
              <td>{w.name}</td>
              <td className="muted">{w.role}</td>
              <td className="muted">{w.kind}</td>
              <td>{zn[w.zone]}</td>
              <td><span className="state" style={{ color: C.status[w.s] }}>{w.s}</span></td>
              <td className="mono">{w.ap || '-'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
