import { useEffect, useState } from 'react'
import { api } from '../services/api'

export default function FillTable(){
  const [d,setD]=useState<any>(null)
  useEffect(()=>{
    const f=async()=>{ try{setD(await api.fills())}catch{}}
    f(); const id=setInterval(f,2000); return()=>clearInterval(id)
  },[])
  const fills = d?.fills || []
  return (
    <div className="p-5 bg-slate-900 border border-slate-800 rounded-2xl overflow-auto">
      <div className="text-sm font-semibold mb-3">Fills <span className="text-slate-500 font-normal">({fills.length}) · {d?.trading_mode}</span></div>
      <table className="w-full text-xs">
        <thead className="text-slate-400"><tr><th className="text-left p-2">Fill ID</th><th>Order ID</th><th>Side</th><th>Price</th><th>Qty</th><th>Notional</th><th>Fee</th></tr></thead>
        <tbody>
          {fills.slice(0,20).map((f:any)=>(
            <tr key={f.fill_id} className="border-t border-slate-800"><td className="p-2 font-mono truncate max-w-[120px]">{f.fill_id}</td><td className="font-mono truncate max-w-[100px]">{f.order_id}</td><td className={`text-center ${f.side==='buy'?'text-emerald-400':'text-red-400'}`}>{f.side}</td><td className="text-right">{Number(f.price).toFixed(2)}</td><td className="text-right">{Number(f.quantity).toFixed(4)}</td><td className="text-right">${Number(f.notional).toFixed(2)}</td><td className="text-right">${Number(f.fee).toFixed(4)}</td></tr>
          ))}
          {fills.length===0 && <tr><td colSpan={7} className="p-4 text-center text-slate-500">No fills yet (PAPER: run bot)</td></tr>}
        </tbody>
      </table>
    </div>
  )
}
