const API = import.meta.env.VITE_API_URL || ''

async function j<T>(url: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`${API}${url}`, { ...init, headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) } })
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`)
  return r.json() as Promise<T>
}

export const api = {
  health: () => j<import('../types').Health>('/api/health'),
  botStatus: () => j<import('../types').BotStatus>('/api/bot/status'),
  botStart: (confirm_live = false) => j<{ ok: boolean }>('/api/bot/start', { method: 'POST', body: JSON.stringify({ confirm_live }) }),
  botStop: () => j<{ ok: boolean }>('/api/bot/stop', { method: 'POST' }),
  botPause: () => j<{ ok: boolean }>('/api/bot/pause', { method: 'POST' }),
  botEmergency: () => j<{ ok: boolean }>('/api/bot/emergency-stop', { method: 'POST' }),
  botReset: () => j<{ ok: boolean }>('/api/bot/reset-emergency', { method: 'POST' }),
  analyticsStatus: () => j<any>('/api/analytics/status'),
  analyticsVolume: () => j<any>('/api/analytics/volume'),
  analyticsPnl: () => j<any>('/api/analytics/pnl'),
  analyticsRisk: () => j<any>('/api/analytics/risk'),
  orders: () => j<any>('/api/orders'),
  fills: () => j<any>('/api/fills'),
  marketSnapshot: () => j<any>('/api/market/snapshot'),
  getSettings: () => j<any>('/api/config/settings'),
  updateSettings: (p: any) => j<any>('/api/config/settings', { method: 'POST', body: JSON.stringify(p) }),
  listMarkets: () => j<any>('/api/markets/list'),
  selectMarket: (market: string) => j<any>('/api/markets/select', { method: 'POST', body: JSON.stringify({ market }) }),
}
