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
  botEmergency: () => j<{ ok: boolean }>('/api/bot/emergency-stop', { method: 'POST' }),
}
