import { useEffect, useState } from 'react'
import { api } from '../services/api'

export default function OrderTable(){
  const [d,setD]=useState<any>(null)
  useEffect(()=>{
    const f=async()=>{ try{setD(await api.orders())}catch{}}
    f(); const id=setInterval(f,2000); return()=>clearInterval(id)
  },[])
  const orders = d?.orders || []
  return (
    <div className="p-5 bg-slate-900 border border-slate-800 rounded-2xl overflow-auto">
      <div className="text-sm font-semibold mb-3">Orders <span className="text-slate-500 font-normal">({orders.length}) · {d?.trading_mode}</span></div>
      <table className="w-full text-xs">
        <thead className="text-slate-400"><tr><th className="text-left p-2">Order ID</th><th>Market</th><th>Side</th><th>Price</th><th>Qty</th><th>Filled</th><th>Remaining</th><th>Status</th></tr></thead>
        <tbody>
          {orders.slice(0,20).map((o:any)=>(
            <tr key={o.order_id} className="border-t border-slate-800"><td className="p-2 font-mono truncate max-w-[120px]">{o.order_id}</td><td className="text-center">{o.market}</td><td className={`text-center ${o.side==='buy'?'text-emerald-400':'text-red-400'}`}>{o.side}</td><td className="text-right">{Number(o.price).toFixed(2)}</td><td className="text-right">{Number(o.quantity).toFixed(4)}</td><td className="text-right">{Number(o.filled_quantity).toFixed(4)}</td><td className="text-right">{Number(o.remaining).toFixed(4)}</td><td className="text-center">{o.status}</td></tr>
          ))}
          {orders.length===0 && <tr><td colSpan={8} className="p-4 text-center text-slate-500">No orders (PAPER sim)</td></tr>}
        </tbody>
      </table>
    </div>
  )
}
