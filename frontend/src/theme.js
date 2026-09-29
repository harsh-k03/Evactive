export const C = {
  bg: '#0a0f14',
  yard: '#0f171f',
  yardGrid: '#131d27',
  floor: '#18222d',
  wall: '#6b7a8c',
  obstacle: '#243140',
  obstacleEdge: '#34465a',
  door: '#1d2935',
  exit: '#22c55e',
  text: '#dbe4ee',
  muted: '#7f8ea3',
  ap: ['#22d3ee', '#a78bfa', '#a3e635', '#f472b6'],
  status: {
    working: '#94a3b8',
    alerted: '#fbbf24',
    evacuating: '#38bdf8',
    safe: '#22c55e',
    trapped: '#ef4444',
    injured: '#f43f5e',
  },
  sensor: { normal: '#475569', A1: '#f59e0b', A2: '#ef4444', alarm: '#ef4444' },
}

export const STAGE_COLORS = {
  0: { bg: '#123524', fg: '#4ade80' },
  1: { bg: '#3a2a07', fg: '#fbbf24' },
  2: { bg: '#3f1d0a', fg: '#fb923c' },
  3: { bg: '#450a0a', fg: '#f87171' },
}

export const AGENT_COLORS = {
  Detection: '#38bdf8',
  Assessment: '#a78bfa',
  Commander: '#f87171',
  Routing: '#22d3ee',
  Comms: '#fbbf24',
  Accountability: '#4ade80',
  Assistant: '#f472b6',
  Simulator: '#64748b',
  System: '#64748b',
}

export const fmtTime = (s) => {
  if (s == null) return '--:--'
  const m = Math.floor(s / 60)
  const ss = String(Math.floor(s % 60)).padStart(2, '0')
  return `${String(m).padStart(2, '0')}:${ss}`
}
