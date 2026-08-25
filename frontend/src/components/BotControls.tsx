import { useEffect, useState } from 'react'
import { api } from '../services/api'

export default function BotControls(){
  const [s,setS]=useState<any>(null)
  const [loading,setLoading]=useState(false)
  const refresh=async()=>{ try{setS(await api.botStatus())}catch{}}
  useEffect(()=>{ refresh(); const id=setInterval(refresh,800); return()=>clearInterval(id)},[])
  if(!s) return null
  const isRunning=s.state==='RUNNING'
  const isLive=s.trading_mode==='LIVE'
  const toggle=async()=>{
    if(loading) return
    setLoading(true)
    try{
      if(isRunning){
        await api.botStop()
      } else {
        if(isLive && !confirm('LIVE: confirm START with real funds? (pure limit maker, 0% taker)')) { setLoading(false); return }
        // Use unified toggle endpoint, fallback to start/stop
        try { await fetch('/api/bot/toggle',{method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({confirm_live: isLive})}).then(r=>r.json()) }
        catch { await api.botStart(isLive) }
      }
      await refresh()
    } finally { setLoading(false) }
  }
  return (
    <div className="p-5 bg-slate-900 border border-slate-800 rounded-2xl flex items-center justify-between">
      <div>
        <div className="text-sm font-semibold">Market Making · Pure Limit (ALO) 0% Taker · Millisecond Quotes</div>
        <div className="text-xs text-slate-400 mt-1">State: <b className={isRunning?'text-emerald-400':'text-slate-300'}>{s.state}</b> · {s.trading_mode} · {s.market} {s.emergency?'· EMERGENCY':''}</div>
      </div>
      <div className="flex items-center gap-2">
        <button onClick={toggle} disabled={loading || s.emergency} className={`px-8 py-3 rounded-xl text-sm font-black tracking-widest border-2 transition ${isRunning?'bg-red-600 hover:bg-red-500 border-red-400 text-white':'bg-emerald-600 hover:bg-emerald-500 border-emerald-400 text-white'} disabled:opacity-50`}>
          {loading?'...': isRunning?'STOP':'START'}
        </button>
        <button onClick={async()=>{await api.botEmergency(); await refresh()}} className="px-3 py-3 bg-red-900 hover:bg-red-800 border border-red-700 rounded-xl text-xs font-bold">EMERGENCY</button>
        {s.emergency && <button onClick={async()=>{await api.botReset(); await refresh()}} className="px-3 py-2 bg-sky-600 hover:bg-sky-500 rounded-lg text-xs">RESET</button>}
      </div>
    </div>
  )
}
