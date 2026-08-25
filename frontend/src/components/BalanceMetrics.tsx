import { useEffect, useState } from 'react'
import { api } from '../services/api'

export default function BalanceMetrics(){
  const [s,setS]=useState<any>(null)
  const [p,setP]=useState<any>(null)
  useEffect(()=>{
    const f=async()=>{
      try{ const st=await api.analyticsStatus(); const pnl=await api.analyticsPnl(); setS(st); setP(pnl)}catch{}
    }
    f(); const id=setInterval(f, 1000); return()=>clearInterval(id)
  },[])
  if(!s||!p) return <div className="p-5 bg-slate-900 border border-slate-800 rounded-2xl">Loading metrics…</div>
  const equity = Number(p.equity ?? s.equity ?? s.account_balance)
  const used = Number(p.used_margin ?? s.used_margin ?? 0)
  const avail = Math.max(0, equity - used)
  const vol = Number(s.volume||0)
  const cpm = Number(p.cpm ?? s.cpm ?? 0)
  return (
    <div className="p-5 bg-slate-900 border border-slate-800 rounded-2xl">
      <div className="text-xs uppercase tracking-widest text-slate-400">Real-Time Balance ($100) · 10x Leverage</div>
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mt-3">
        <div className="bg-slate-800/60 p-3 rounded-xl border border-slate-700"><div className="text-xs text-slate-400">Total Equity</div><div className="text-lg font-bold text-emerald-400">${equity.toFixed(2)}</div><div className="text-xs text-slate-500">Bal ${Number(s.account_balance).toFixed(0)} + PnL</div></div>
        <div className="bg-slate-800/60 p-3 rounded-xl border border-slate-700"><div className="text-xs text-slate-400">Used Margin (10x)</div><div className="text-lg font-bold text-amber-400">${used.toFixed(2)}</div><div className="text-xs text-slate-500">Avail ${avail.toFixed(2)}</div></div>
        <div className="bg-slate-800/60 p-3 rounded-xl border border-slate-700"><div className="text-xs text-slate-400">Cumulative Volume</div><div className="text-lg font-bold">${vol.toLocaleString(undefined,{maximumFractionDigits:0})}</div><div className="text-xs text-slate-500">Target $1M</div></div>
        <div className="bg-slate-800/60 p-3 rounded-xl border border-slate-700"><div className="text-xs text-slate-400">Net PnL</div><div className={`text-lg font-bold ${Number(p.net)>=0?'text-emerald-400':'text-red-400'}`}>${Number(p.net).toFixed(4)}</div><div className="text-xs text-slate-500">Real ${Number(p.realized).toFixed(4)} + Unr {Number(p.unrealized).toFixed(4)}</div></div>
        <div className="bg-sky-900/30 p-3 rounded-xl border border-sky-700"><div className="text-xs text-slate-400">Verified CPM</div><div className="text-lg font-bold text-sky-300">${cpm.toFixed(2)}/1M</div><div className="text-xs text-slate-500">$/1M volume</div></div>
      </div>
      <div className="text-xs text-slate-500 mt-2">Micro TP ${Number(s.take_profit_usd).toFixed(3)} · SL ${Number(s.stop_loss_usd).toFixed(3)} &lt;$0.01 · Strict sub-cent stop eliminates inventory risk</div>
    </div>
  )
}
