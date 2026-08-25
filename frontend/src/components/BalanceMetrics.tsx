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
  const position = Number(s.margin_usd || 5) * Number(s.leverage || 10)
  const maxLev = Number(s.max_leverage_for_pair || s.leverage || 10)
  return (
    <div className="p-5 bg-slate-900 border border-slate-800 rounded-2xl">
      <div className="text-xs uppercase tracking-widest text-slate-400">Real-Time Balance · Margin × Leverage (Arcus max {maxLev}x for {s.market})</div>
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mt-3">
        <div className="bg-slate-800/60 p-3 rounded-xl border border-slate-700"><div className="text-xs text-slate-400">Total Equity</div><div className="text-lg font-bold text-emerald-400">${equity.toFixed(2)}</div><div className="text-xs text-slate-500">Bal ${Number(s.account_balance).toFixed(0)} · Margin ${Number(s.margin_usd||5).toFixed(0)}</div></div>
        <div className="bg-amber-900/20 p-3 rounded-xl border border-amber-700"><div className="text-xs text-slate-400">Active Used Margin</div><div className="text-lg font-bold text-amber-400">${used.toFixed(2)}</div><div className="text-xs text-slate-500">Position ${position.toFixed(0)} ({s.margin_usd}×{s.leverage}) · Avail ${avail.toFixed(2)}</div></div>
        <div className="bg-slate-800/60 p-3 rounded-xl border border-slate-700"><div className="text-xs text-slate-400">Cumulative Volume</div><div className="text-lg font-bold">${vol.toLocaleString(undefined,{maximumFractionDigits:0})}</div><div className="text-xs text-slate-500">Target $1M · Open lim notional</div></div>
        <div className="bg-slate-800/60 p-3 rounded-xl border border-slate-700"><div className="text-xs text-slate-400">Net PnL (sub-cent exact)</div><div className={`text-lg font-bold ${Number(p.net)>=0?'text-emerald-400':'text-red-400'}`}>${Number(p.net).toFixed(3)}</div><div className="text-xs text-slate-500">Real ${Number(p.realized).toFixed(3)} · Unr {Number(p.unrealized).toFixed(3)}</div></div>
        <div className="bg-sky-900/30 p-3 rounded-xl border border-sky-700"><div className="text-xs text-slate-400">Verified CPM</div><div className="text-lg font-bold text-sky-300">${cpm.toFixed(2)}/1M</div><div className="text-xs text-slate-500">Losses e.g. -0.006 shown red</div></div>
      </div>
      <div className="text-xs text-slate-500 mt-2">Live {s.market}  BID {Number(s.bid).toFixed(2)} / ASK {Number(s.ask).toFixed(2)} / MID {Number(s.mid).toFixed(2)} · Spread {Number(s.spread_bps).toFixed(1)} bps · TP ${Number(s.take_profit_usd).toFixed(3)} · SL ${Number(s.stop_loss_usd).toFixed(3)} &lt;$0.01</div>
    </div>
  )
}
