import { useEffect, useState } from 'react'
import { api } from '../services/api'

function Bar({pct, label}:{pct:number,label:string}){
  const c = pct>90?'bg-red-500':pct>70?'bg-amber-500':'bg-emerald-500'
  return (
    <div className="mb-3">
      <div className="flex justify-between text-xs text-slate-400"><span>{label}</span><span>{pct.toFixed(1)}%</span></div>
      <div className="w-full h-2 bg-slate-800 rounded-full mt-1 overflow-hidden"><div className={`h-full ${c}`} style={{width:`${Math.min(100,pct)}%`}} /></div>
    </div>
  )
}

export default function RiskDashboard(){
  const [r,setR]=useState<any>(null)
  useEffect(()=>{
    const f=async()=>{ try{setR(await api.analyticsRisk())}catch{}}
    f(); const id=setInterval(f,2000); return()=>clearInterval(id)
  },[])
  if(!r) return <div className="p-5 bg-slate-900 border border-slate-800 rounded-2xl">Loading risk…</div>
  return (
    <div className="p-5 bg-slate-900 border border-slate-800 rounded-2xl">
      <div className="text-sm font-semibold">Risk Dashboard <span className={`ml-2 text-xs px-2 py-0.5 rounded ${r.overall==='OK'?'bg-emerald-900 text-emerald-300':'bg-red-900 text-red-300'}`}>{r.overall}</span></div>
      <div className="mt-4">
        <Bar pct={r.inventory_usage_pct} label="Inventory usage" />
        <Bar pct={r.exposure_usage_pct} label="Exposure usage" />
        <Bar pct={r.daily_loss_usage_pct} label="Daily loss usage" />
        <Bar pct={r.open_order_usage_pct} label="Open orders" />
        <Bar pct={r.rate_limit_usage_pct} label="Rate limit" />
      </div>
      <div className="text-xs text-slate-400 mt-2">Stale: {String(r.stale)} · DMS: {String(r.dms_active)} · Inv: {Number(r.inventory).toFixed(4)} · Exp: ${Number(r.exposure).toFixed(2)}</div>
    </div>
  )
}
