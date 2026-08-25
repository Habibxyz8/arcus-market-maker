import { useEffect, useState } from 'react'
import { api } from '../services/api'
import type { BotStatus } from '../types'

export default function StatusCard() {
  const [s, setS] = useState<BotStatus | null>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    let id = setInterval(async () => {
      try { setS(await api.botStatus()); setErr(null) } catch (e: unknown) { setErr(e instanceof Error ? e.message : String(e)) }
    }, 2000)
    api.botStatus().then(setS).catch(e => setErr(String(e)))
    return () => clearInterval(id)
  }, [])

  if (err) return <div className="p-4 bg-red-900/40 border border-red-800 rounded-xl text-sm">Backend offline: {err}</div>
  if (!s) return <div className="p-4 bg-slate-900 border border-slate-800 rounded-xl text-sm">Loading…</div>

  const color = s.state === 'RUNNING' ? 'text-emerald-400' : s.state === 'EMERGENCY' ? 'text-red-400' : 'text-slate-300'
  return (
    <div className="p-5 bg-slate-900 border border-slate-800 rounded-2xl">
      <div className="text-xs uppercase tracking-widest text-slate-400">Bot Status</div>
      <div className={`text-2xl font-bold mt-1 ${color}`}>{s.state}</div>
      <div className="text-sm text-slate-400 mt-1">{s.trading_mode} · {s.market} {s.emergency ? '· EMERGENCY' : ''}</div>
      <div className="flex gap-2 mt-4">
        <button onClick={() => api.botStart(s.trading_mode === 'LIVE').catch(()=>{})} className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 rounded-lg text-sm font-medium">START</button>
        <button onClick={() => api.botStop().catch(()=>{})} className="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 rounded-lg text-sm">STOP</button>
        <button onClick={() => api.botEmergency().catch(()=>{})} className="px-3 py-1.5 bg-red-600 hover:bg-red-500 rounded-lg text-sm font-semibold">EMERGENCY STOP</button>
      </div>
    </div>
  )
}
