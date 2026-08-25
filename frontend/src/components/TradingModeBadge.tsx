import { useEffect, useState } from 'react'

type ModeInfo = { mode: string; is_paper: boolean; is_testnet: boolean; is_live: boolean; market: string; has_credentials: boolean }

export default function TradingModeBadge() {
  const [m, setM] = useState<ModeInfo | null>(null)
  useEffect(() => {
    fetch('/api/config/mode').then(r=>r.json()).then(setM).catch(()=>{})
    const id = setInterval(()=>fetch('/api/config/mode').then(r=>r.json()).then(setM).catch(()=>{}), 5000)
    return ()=>clearInterval(id)
  }, [])
  if (!m) return <span className="text-xs px-2 py-1 rounded bg-slate-800 border border-slate-700">…</span>
  const cls = m.is_live ? 'bg-red-900/50 border-red-700 text-red-300' : m.is_testnet ? 'bg-amber-900/30 border-amber-700 text-amber-300' : 'bg-emerald-900/30 border-emerald-700 text-emerald-300'
  return (
    <span className={`text-xs px-2.5 py-1 rounded-full border font-semibold tracking-widest ${cls}`}>
      {m.mode} {m.is_live ? '· CONFIRM REQUIRED' : m.is_paper ? '· SAFE' : '· TESTNET'} {!m.has_credentials && (m.is_live||m.is_testnet) ? '· NO CREDS' : ''}
    </span>
  )
}
