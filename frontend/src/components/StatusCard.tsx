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
  const isLive = s.trading_mode === 'LIVE'

  async function handleStart() {
    if (isLive) {
      const ok = window.confirm('LIVE mode will place REAL orders with real funds. Confirm START LIVE?')
      if (!ok) return
    }
    try { await api.botStart(isLive); setS(await api.botStatus()) } catch (e: unknown) { alert(e instanceof Error ? e.message : String(e)) }
  }

  return (
    <div className="p-5 bg-slate-900 border border-slate-800 rounded-2xl">
      <div className="text-xs uppercase tracking-widest text-slate-400">Bot Status</div>
      <div className={`text-2xl font-bold mt-1 ${color}`}>{s.state}</div>
      <div className="text-sm text-slate-400 mt-1">{s.trading_mode} · {s.market} {s.emergency ? '· EMERGENCY' : ''} {isLive ? '· LIVE GATED' : ''}</div>
      <div className="flex gap-2 mt-4 flex-wrap">
        <button onClick={handleStart} className={`px-3 py-1.5 rounded-lg text-sm font-medium ${isLive ? 'bg-red-600 hover:bg-red-500' : 'bg-emerald-600 hover:bg-emerald-500'}`}>{isLive ? 'START LIVE' : 'START'}</button>
        <button onClick={async ()=>{ await api.botStop(); setS(await api.botStatus())}} className="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 rounded-lg text-sm">STOP</button>
        <button onClick={async ()=>{ await api.botEmergency(); setS(await api.botStatus())}} className="px-3 py-1.5 bg-red-600 hover:bg-red-500 rounded-lg text-sm font-semibold">EMERGENCY STOP</button>
        {s.emergency && <button onClick={async ()=>{ await fetch('/api/bot/reset-emergency',{method:'POST'}); setS(await api.botStatus())}} className="px-3 py-1.5 bg-amber-600 hover:bg-amber-500 rounded-lg text-sm">RESET EMERGENCY</button>}
      </div>
      {isLive && <div className="text-xs text-red-300 mt-2">LIVE requires explicit confirm_live + credentials. Default is PAPER.</div>}
    </div>
  )
}
