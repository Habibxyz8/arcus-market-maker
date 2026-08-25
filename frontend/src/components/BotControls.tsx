import { useEffect, useState } from 'react'
import { api } from '../services/api'

export default function BotControls(){
  const [s,setS]=useState<any>(null)
  const refresh=async()=>{ try{setS(await api.botStatus())}catch{}}
  useEffect(()=>{ refresh(); const id=setInterval(refresh,2000); return()=>clearInterval(id)},[])
  if(!s) return null
  const isLive=s.trading_mode==='LIVE'
  return (
    <div className="p-5 bg-slate-900 border border-slate-800 rounded-2xl">
      <div className="text-sm font-semibold">Bot Controls</div>
      <div className="flex gap-2 mt-3 flex-wrap">
        <button onClick={async()=>{
          if(isLive && !confirm('LIVE: confirm START with real funds?')) return
          await api.botStart(isLive); await refresh()
        }} className={`px-4 py-2 rounded-lg text-sm font-bold ${isLive?'bg-red-600 hover:bg-red-500':'bg-emerald-600 hover:bg-emerald-500'}`}>START {isLive?'(LIVE)':''}</button>
        <button onClick={async()=>{await api.botPause(); await refresh()}} className="px-4 py-2 bg-amber-600 hover:bg-amber-500 rounded-lg text-sm">PAUSE</button>
        <button onClick={async()=>{await api.botStop(); await refresh()}} className="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-sm">STOP</button>
        <button onClick={async()=>{await api.botEmergency(); await refresh()}} className="px-4 py-2 bg-red-700 hover:bg-red-600 rounded-lg text-sm font-bold border border-red-500">EMERGENCY STOP</button>
        {s.emergency && <button onClick={async()=>{await api.botReset(); await refresh()}} className="px-4 py-2 bg-sky-600 hover:bg-sky-500 rounded-lg text-sm">RESET EMERGENCY</button>}
      </div>
      <div className="text-xs text-slate-400 mt-2">State: {s.state} · Emergency: {String(s.emergency)} {isLive?'· LIVE requires confirm_live':''}</div>
    </div>
  )
}
