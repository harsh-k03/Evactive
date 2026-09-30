async function post(path, body) {
  const r = await fetch(`/api${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  })
  const data = await r.json().catch(() => ({}))
  if (!r.ok) throw new Error(data.detail || r.statusText)
  return data
}

export const api = {
  reset: (scenario_id, autostart = false, layout_id = 'float-glass') =>
    post('/sim/reset', { layout_id, scenario_id, autostart }),
  play: () => post('/sim/play'),
  pause: () => post('/sim/pause'),
  step: () => post('/sim/step'),
  speed: (speed) => post('/sim/speed', { speed }),
  hazard: (type, x, y, extra = {}) => post('/hazard', { type, x, y, ...extra }),
  wind: (from_deg, speed_mps) => post('/wind', { from_deg, speed_mps }),
  evacuate: (scope) => post('/evacuate', { scope }),
  isolate: (leak_ids = null) => post('/isolate', { leak_ids }),
  ask: (question) => post('/ask', { question }),
  llm: (enabled) => post('/llm', { enabled }),
}
