import { useEffect, useState } from 'react'
import { api } from '../services/api'

export default function PnLCards() {
  const [p, setP] = useState<any>(null)
  useEffect(()=>{
    const f=async()=>{ try{setP(await api.analyticsPnl())}catch{}}
    f(); const id=setInterval(f,2000); return()=>clearInterval(id)
  },[])
  if(!p) return <div className="p-5 bg-slate-900 border border-slate-800 rounded-2xl">Loading PnL…</div>
  const items = [
    {label:'Gross PnL', value:p.gross},
    {label:'Fees', value:p.fees},
    {label:'Funding', value:p.funding},
    {label:'Inventory PnL', value:p.inventory_pnl},
    {label:'Net PnL', value:p.net, highlight:true},
  ]
  return (
    <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
      {items.map(it=>(
        <div key={it.label} className={`p-4 rounded-2xl border ${it.highlight?'bg-sky-900/30 border-sky-700':'bg-slate-900 border-slate-800'}`}>
          <div className="text-xs uppercase tracking-widest text-slate-400">{it.label}</div>
          <div className={`text-lg font-bold mt-1 ${Number(it.value)>=0?'text-emerald-400':'text-red-400'}`}>${Number(it.value||0).toFixed(2)}</div>
        </div>
      ))}
    </div>
  )
}
