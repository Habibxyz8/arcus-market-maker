import { useEffect, useState } from 'react'
import { api } from '../services/api'

export default function VolumeCard() {
  const [v, setV] = useState<any>(null)
  useEffect(()=>{
    const f=async()=>{ try{setV(await api.analyticsVolume())}catch{}}
    f(); const id=setInterval(f, 2000); return()=>clearInterval(id)
  },[])
  if(!v) return <div className="p-5 bg-slate-900 border border-slate-800 rounded-2xl">Loading volume…</div>
  const pct = Math.min(100, v.progress_pct||0)
  return (
    <div className="p-5 bg-slate-900 border border-slate-800 rounded-2xl">
      <div className="text-xs uppercase tracking-widest text-slate-400">$1,000,000 Target</div>
      <div className="mt-2 flex items-baseline gap-2">
        <span className="text-2xl font-bold">${(v.current||0).toLocaleString(undefined,{maximumFractionDigits:0})}</span>
        <span className="text-sm text-slate-400">/ $1,000,000</span>
        <span className={`ml-auto text-sm font-semibold ${pct>50?'text-emerald-400':'text-amber-400'}`}>{pct.toFixed(2)}%</span>
      </div>
      <div className="w-full h-2 bg-slate-800 rounded-full mt-3 overflow-hidden">
        <div className="h-full bg-sky-500" style={{width: `${pct}%`}} />
      </div>
      <div className="grid grid-cols-3 gap-3 mt-4 text-xs">
        <div><div className="text-slate-400">Remaining</div><div className="font-semibold">${(v.remaining||0).toLocaleString()}</div></div>
        <div><div className="text-slate-400">Daily</div><div className="font-semibold">${(v.daily||0).toLocaleString()}</div></div>
        <div><div className="text-slate-400">Session</div><div className="font-semibold">${(v.session||0).toLocaleString()}</div></div>
      </div>
      <div className="text-xs text-slate-500 mt-2">Mode: {v.trading_mode} · Fills: {v.fills} · Avg: ${Number(v.avg_fill||0).toFixed(2)}</div>
      <div className="text-xs text-amber-300 mt-1">Paper/ Testnet/ Live volumes strictly separated (Phase 24)</div>
    </div>
  )
}
