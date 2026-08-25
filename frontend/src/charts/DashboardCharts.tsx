import { useEffect, useState } from 'react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import { api } from '../services/api'

function Chart({title, dataKey, data}:{title:string, dataKey:string, data:any[]}){
  return (
    <div className="p-4 bg-slate-900 border border-slate-800 rounded-2xl">
      <div className="text-xs uppercase tracking-widest text-slate-400 mb-2">{title}</div>
      <ResponsiveContainer width="100%" height={160}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
          <XAxis dataKey="t" hide />
          <YAxis tick={{fontSize:10, fill:'#9ca3af'}} width={50} />
          <Tooltip contentStyle={{background:'#111827', border:'1px solid #1f2937', fontSize:12}} />
          <Line type="monotone" dataKey={dataKey} stroke="#38bdf8" dot={false} strokeWidth={1.5} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

export default function DashboardCharts(){
  const [pts, setPts]=useState<any[]>([])
  useEffect(()=>{
    const id=setInterval(async()=>{
      try{
        const s=await api.analyticsStatus()
        const p=await api.analyticsPnl()
        setPts(prev=>{
          const nxt=[...prev, {t:new Date().toLocaleTimeString(), volume:s.volume, pnl:p.net, inventory:s.inventory, spread:s.spread||0, fees:p.fees}]
          return nxt.slice(-40)
        })
      }catch{}
    },2000)
    return()=>clearInterval(id)
  },[])
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <Chart title="Volume over time" dataKey="volume" data={pts} />
      <Chart title="PnL over time" dataKey="pnl" data={pts} />
      <Chart title="Inventory over time" dataKey="inventory" data={pts} />
      <Chart title="Spread over time" dataKey="spread" data={pts} />
      <Chart title="Fees over time" dataKey="fees" data={pts} />
      <Chart title="Volume (duplicate for fill-rate placeholder)" dataKey="volume" data={pts} />
    </div>
  )
}
