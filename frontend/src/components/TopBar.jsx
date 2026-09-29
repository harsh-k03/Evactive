import { useEffect, useState } from 'react'
import { api } from '../api'
import { STAGE_COLORS, fmtTime } from '../theme'

const SPEEDS = [1, 2, 4, 8]

export default function TopBar({ init, frame, connected, onError }) {
  const [scenario, setScenario] = useState('')
  const [layoutId, setLayoutId] = useState(null)
  // follow whatever the server has loaded (also when another dashboard changes it)
  useEffect(() => {
    setLayoutId(null)
    setScenario(init?.scenario || '')
  }, [init?.layout?.id, init?.scenario, init?.frame?.run])
  const currentLayout = layoutId || init?.layout?.id
  const scenarios = init?.layouts?.find((l) => l.id === currentLayout)?.scenarios || []
  const f = frame
  const stage = STAGE_COLORS[f?.stage ?? 0]
  const since = f?.started_t != null ? f.t - f.started_t : null
  const run = (p) => p.catch((e) => onError?.(e.message))

  return (
    <header className="topbar">
      <div className="brand">
        <div className="logo">
          <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true">
            <path d="M4 20 L12 4 L20 20 Z" fill="none" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
            <path d="M12 10 L12 14 M12 16.5 L12 17" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
        </div>
        <div>
          <div className="brand-name">EVACTIVE</div>
          <div className="brand-sub">{init?.layout?.name || 'connecting...'}</div>
        </div>
      </div>

      <div className="stage" style={{ background: stage.bg, color: stage.fg, borderColor: stage.fg }}>
        <span className={`dot ${f?.stage >= 2 ? 'blink' : ''}`} style={{ background: stage.fg }} />
        {f?.stage_label || 'NORMAL'}
      </div>

      <div className="clocks">
        <div><span className="k">SIM</span> <span className="mono">{fmtTime(f?.t)}</span></div>
        <div><span className="k">INCIDENT</span> <span className="mono">{since != null ? fmtTime(since) : '--:--'}</span></div>
        {f?.all_clear_t != null && <div className="allclear">ALL CLEAR @ {fmtTime(f.all_clear_t - (f.started_t || 0))}</div>}
      </div>

      <div className="controls">
        <select className="layout-pick" value={currentLayout || ''} title="Plant layout"
          onChange={(e) => { setLayoutId(e.target.value); setScenario('') }}>
          {init?.layouts?.map((l) => <option key={l.id} value={l.id}>{l.name.split(' - ')[0].replace(' (sample)', '')}</option>)}
        </select>
        <select value={scenario} onChange={(e) => setScenario(e.target.value)} title="Scenario">
          <option value="">Free play (click the map to add hazards)</option>
          {scenarios.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
        </select>
        <button className={`btn ${currentLayout !== init?.layout?.id ? 'pending' : ''}`}
          onClick={() => run(api.reset(scenario || null, false, currentLayout))}
          title="Load the selected plant and scenario">{currentLayout !== init?.layout?.id ? 'Load' : 'Reset'}</button>
        {f?.running
          ? <button className="btn primary" onClick={() => run(api.pause())}>Pause</button>
          : <button className="btn primary" onClick={() => run(api.play())}>Run</button>}
        <button className="btn" onClick={() => run(api.step())} disabled={f?.running} title="Advance one second">Step</button>
        <div className="seg" title="Simulation speed">
          {SPEEDS.map((s) => (
            <button key={s} className={f?.speed === s ? 'on' : ''} onClick={() => run(api.speed(s))}>{s}x</button>
          ))}
        </div>
      </div>

      <div className="status">
        <span className={`pill ${connected ? 'ok' : 'bad'}`}>{connected ? 'LIVE' : 'OFFLINE'}</span>
        <span className={`pill ${f?.llm?.online ? 'ok' : 'warn'}`}
          title={f?.llm?.online ? `${f.llm.calls} LLM calls, ${f.llm.tokens} tokens this session · last reply ${f.llm.latency_ms ?? '-'} ms` : (f?.llm?.error || f?.llm?.url)}>
          LLM {f?.llm?.online ? f.llm.model : 'offline'}
        </span>
      </div>
    </header>
  )
}
