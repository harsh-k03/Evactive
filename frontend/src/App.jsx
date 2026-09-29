import { useEffect, useRef, useState } from 'react'
import { api } from './api'
import BottomPanel from './components/BottomPanel'
import PlantMap from './components/PlantMap'
import Sidebar from './components/Sidebar'
import TopBar from './components/TopBar'
import { C } from './theme'
import { useEvactive } from './useEvactive'

export default function App() {
  const { init, frame, frameRef, frameGap, log, connected } = useEvactive()
  const [tool, setTool] = useState('inspect')
  const gases = init?.layout?.gases || ['Natural gas (CH4)']
  const [gasPick, setGas] = useState(null)
  const gas = gases.includes(gasPick) ? gasPick : gases[0]
  const [layers, setLayers] = useState({ routes: true, gas: true, smoke: true, sensors: true, queues: true })
  const [focusWorker, setFocusWorker] = useState(null)
  const [toast, setToast] = useState(null)
  const [wind, setWind] = useState(null)

  const dragging = useRef(false)
  // keep the wind sliders in sync with the server (scenarios set their own wind)
  useEffect(() => {
    if (!frame || dragging.current) return
    const w = { from: frame.wind.from_deg, speed: frame.wind.speed_mps }
    if (!wind || w.from !== wind.from || w.speed !== wind.speed) setWind(w)
  }, [frame?.wind?.from_deg, frame?.wind?.speed_mps])
  const commitWind = () => {
    dragging.current = false
    api.wind(wind.from, wind.speed).catch((e) => setToast(e.message))
  }
  useEffect(() => {
    if (!toast) return
    const t = setTimeout(() => setToast(null), 3500)
    return () => clearTimeout(t)
  }, [toast])

  const onCellClick = (x, y) => {
    if (tool === 'fire') api.hazard('fire', x, y).catch((e) => setToast(e.message))
    else if (tool === 'leak') api.hazard('leak', x, y, { gas, rate: 320 }).catch((e) => setToast(e.message))
  }
  const toggle = (k) => setLayers((l) => ({ ...l, [k]: !l[k] }))

  return (
    <div className="app">
      <TopBar init={init} frame={frame} connected={connected} onError={setToast} />
      <main className="main">
        <div className="center">
          <div className="map-card">
            <div className="map-toolbar">
              <div className="seg">
                <button className={tool === 'inspect' ? 'on' : ''} onClick={() => setTool('inspect')}>Inspect</button>
                <button className={tool === 'fire' ? 'on fire' : ''} onClick={() => setTool('fire')}>+ Fire</button>
                <button className={tool === 'leak' ? 'on leak' : ''} onClick={() => setTool('leak')}>+ Gas leak</button>
              </div>
              {tool === 'leak' && (
                <select value={gas} onChange={(e) => setGas(e.target.value)}>
                  {gases.map((g) => <option key={g}>{g}</option>)}
                </select>
              )}
              <div className="layers">
                {Object.keys(layers).map((k) => (
                  <label key={k}><input type="checkbox" checked={layers[k]} onChange={() => toggle(k)} /> {k}</label>
                ))}
              </div>
              {wind && (
                <div className="wind">
                  <span className="muted">Wind from</span>
                  <input type="range" min="0" max="345" step="15" value={wind.from}
                    onPointerDown={() => { dragging.current = true }}
                    onChange={(e) => setWind({ ...wind, from: +e.target.value })}
                    onPointerUp={commitWind} />
                  <span className="mono">{String(Math.round(wind.from)).padStart(3, '0')}°</span>
                  <input type="range" min="0" max="8" step="0.5" value={wind.speed}
                    onPointerDown={() => { dragging.current = true }}
                    onChange={(e) => setWind({ ...wind, speed: +e.target.value })}
                    onPointerUp={commitWind} />
                  <span className="mono">{wind.speed.toFixed(1)} m/s</span>
                </div>
              )}
            </div>
            {init ? (
              <PlantMap init={init} frameRef={frameRef} frameGap={frameGap} layers={layers} tool={tool}
                onCellClick={onCellClick} focusWorker={focusWorker} />
            ) : (
              <div className="map-wrap empty">Connecting to Evactive server...</div>
            )}
            <Legend />
          </div>
          <BottomPanel init={init} frame={frame} log={log} onFocusWorker={setFocusWorker} focusWorker={focusWorker} />
        </div>
        <Sidebar init={init} frame={frame} onError={setToast} />
      </main>
      {toast && <div className="toast">{toast}</div>}
    </div>
  )
}

function Legend() {
  const people = ['working', 'alerted', 'evacuating', 'safe', 'trapped']
  return (
    <div className="legend">
      {people.map((s) => <span key={s}><i className="dotc" style={{ background: C.status[s] }} />{s}</span>)}
      <span><i className="shape diamond" />gas detector</span>
      <span><i className="shape tri" />flame detector</span>
      <span><i className="shape circ" />smoke detector</span>
      <span><i className="sw" style={{ background: 'rgba(250,204,21,.6)' }} />&lt;20% LEL</span>
      <span><i className="sw" style={{ background: 'rgba(249,115,22,.7)' }} />20-40%</span>
      <span><i className="sw" style={{ background: 'rgba(217,70,239,.8)' }} />&gt;40% LEL</span>
      <span><i className="sw" style={{ background: 'rgba(148,163,184,.6)' }} />smoke</span>
      <span><i className="sw" style={{ background: '#ff6a00' }} />fire</span>
      <span><i className="ringc" />bottleneck (queue)</span>
      <span className="muted">1 cell = 2 m · sample layout, not to scale</span>
    </div>
  )
}
