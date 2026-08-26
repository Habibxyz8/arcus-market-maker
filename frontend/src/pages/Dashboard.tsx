import TradingModeBadge from '../components/TradingModeBadge'
import TradeHistory from '../components/TradeHistory'
import { useEffect, useState } from 'react'
import { api } from '../services/api'

function ControlPanel(){
  const [s,setS]=useState<any>(null)
  const [isRunning,setIsRunning]=useState(false)
  const [margin,setMargin]=useState('')
  const [lev,setLev]=useState('')
  const [limits,setLimits]=useState<any>({})
  const load=async()=>{
    try{
      const j=await api.getSettings()
      const st=await api.botStatus()
      setS(j); setIsRunning(st.state==='RUNNING')
      try{
        const lim=await fetch('/api/markets/limits').then(r=>r.json())
        if(lim.limits){
          setLimits(lim.limits)
          const liveMarkets=Object.keys(lim.limits).sort()
          if(liveMarkets.length) j.supported_markets=liveMarkets
          setS({...j})
        }
      }catch{}
    }catch{}
  }
  useEffect(()=>{ load(); const id=setInterval(load,4000); return()=>clearInterval(id)},[])
  const toggle=async()=>{
    const st=await api.botStatus()
    if(st.state==='RUNNING') await fetch('/api/bot/toggle',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'})
    else {
      if(st.trading_mode==='LIVE' && !confirm('LIVE confirm?')) return
      await fetch('/api/bot/toggle',{method:'POST',headers:{'Content-Type':'application/json'},body: JSON.stringify({confirm_live: st.trading_mode==='LIVE'})})
    }
    await load()
  }
  const applyMarginLev=async()=>{
    const p:any={}
    if(margin) p.margin_usd=parseFloat(margin)
    if(lev) p.leverage=parseInt(lev)
    if(!Object.keys(p).length) return
    await api.updateSettings(p); setMargin(''); setLev(''); await load()
  }
  if(!s) return <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5">Loading…</div>
  const maxLev=s.max_leverage_for_pair||10
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 flex flex-col md:flex-row gap-4 items-start md:items-center">
      <button onClick={toggle} className={`px-10 py-4 rounded-xl font-black tracking-widest text-sm border-2 min-w-[140px] ${isRunning?'bg-red-600 border-red-400 hover:bg-red-500 text-white':'bg-emerald-600 border-emerald-400 hover:bg-emerald-500 text-white'}`}>
        {isRunning?'STOP':'START'}
      </button>
      <div className="flex-1 grid grid-cols-1 md:grid-cols-3 gap-3 w-full">
        <label className="bg-slate-800 rounded-xl px-3 py-2 border border-slate-700">
          <div className="text-xs text-slate-400">Margin $1-100+</div>
          <div className="flex gap-2 mt-1">
            <input value={margin} onChange={e=>setMargin(e.target.value)} placeholder={`${s.margin_usd}`} className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-sm" />
            <span className="text-xs text-slate-500 py-1">× {s.leverage}x = ${Math.round(s.margin_usd*s.leverage)}</span>
          </div>
        </label>
        <label className="bg-slate-800 rounded-xl px-3 py-2 border border-slate-700">
          <div className="text-xs text-slate-400">Leverage (max {maxLev}x {s.market})</div>
          <div className="flex gap-2 mt-1">
            <input value={lev} onChange={e=>setLev(e.target.value)} placeholder={`${s.leverage}x`} className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-sm" />
            <button onClick={applyMarginLev} className="px-3 bg-sky-600 hover:bg-sky-500 rounded text-xs font-bold">Set</button>
          </div>
        </label>
        <label className="bg-slate-800 rounded-xl px-3 py-2 border border-slate-700">
          <div className="text-xs text-slate-400">Pair · Max Leverage</div>
          <select value={s.market} onChange={async e=>{ await fetch('/api/markets/select',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({market:e.target.value})}); await load()}} className="w-full mt-1 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-sm">
            <option value="ALL_PAIRS">ALL PAIRS (Auto Multi-Pair) — maximize volume</option>
            {(s.supported_markets||[]).map((m:string)=>{
              const levM = limits[m]?.max_leverage || (m.includes('BTC')?20:m.includes('ETH')?15:m.includes('SOL')?10:5)
              return <option key={m} value={m}>{m} (Max {levM}x)</option>
            })}
          </select>
        </label>
      </div>
      <div className="text-xs text-slate-500 hidden md:block">ALO maker · {s.strategy_preset} · TP ${Number(s.take_profit_usd).toFixed(3)} SL {Number(s.stop_loss_usd).toFixed(3)}</div>
    </div>
  )
}

function ExecutionStatus(){
  const [txt,setTxt]=useState('IDLE')
  const [isRunning,setIsRunning]=useState(false)
  useEffect(()=>{
    let ws: WebSocket|null=null
    const connect=()=>{
      try{
        const proto=location.protocol==='https:'?'wss:':'ws:'
        ws=new WebSocket(`${proto}//${location.host}/api/ws/dashboard`)
        ws.onmessage=e=>{ try{ const j=JSON.parse(e.data); if(j.execution_status) setTxt(j.execution_status); if(j.state) setIsRunning(j.state==='RUNNING')}catch{}}
        ws.onclose=()=> setTimeout(connect,1200)
      }catch{}
    }
    connect()
    const id=setInterval(async()=>{ try{ const r=await fetch('/api/analytics/status').then(r=>r.json()); if(r.execution_status) setTxt(r.execution_status); setIsRunning(r.state==='RUNNING')}catch{}},700)
    return()=>{ try{ws?.close()}catch{}; clearInterval(id)}
  },[])
  return <div className={`px-3 py-1.5 rounded-full text-xs font-mono border flex items-center gap-2 ${isRunning? 'bg-slate-800 border-slate-700 text-amber-300' : 'bg-slate-900 border-slate-800 text-slate-500'}`}><span className={`w-2 h-2 rounded-full ${isRunning?'bg-emerald-400 animate-pulse':'bg-slate-600'}`}/>{txt}</div>
}

function MetricCards(){
  const [s,setS]=useState<any>(null)
  const [p,setP]=useState<any>(null)
  useEffect(()=>{
    let ws: WebSocket|null=null
    try{
      const proto=location.protocol==='https:'?'wss:':'ws:'
      ws=new WebSocket(`${proto}//${location.host}/api/ws/dashboard`)
      ws.onmessage=e=>{ try{ const j=JSON.parse(e.data); if(j.volume!==undefined) setS(j); if(j.cpm!==undefined) setP({equity:j.equity, used_margin:j.used_margin, net:j.net_pnl, realized:j.realized_pnl, cpm:j.cpm, volume:j.volume})}catch{}}
    }catch{}
    const f=async()=>{ try{ const st=await api.analyticsStatus(); const pn=await api.analyticsPnl(); setS(st); setP(pn)}catch{}}
    f(); const id=setInterval(f,600); return()=>{ try{ws?.close()}catch{}; clearInterval(id)}
  },[])
  if(!s||!p) return <div className="grid grid-cols-2 md:grid-cols-5 gap-3"><div className="h-24 bg-slate-900 rounded-2xl animate-pulse"/><div className="h-24 bg-slate-900 rounded-2xl animate-pulse"/><div className="h-24 bg-slate-900 rounded-2xl animate-pulse"/><div className="h-24 bg-slate-900 rounded-2xl animate-pulse"/><div className="h-24 bg-slate-900 rounded-2xl animate-pulse"/></div>
  const cards=[
    {label:'Total Equity', value:`$${Number(p.equity).toFixed(2)}`, sub:`$${Number(s.account_balance).toFixed(0)} base`, color:'text-emerald-400'},
    {label:'Active Used Margin', value:`$${Number(p.used_margin).toFixed(2)}`, sub:`Avail $${(Number(p.equity)-Number(p.used_margin)).toFixed(2)}`, color:'text-amber-400'},
    {label:'Cumulative Volume', value:`$${Number(s.volume).toLocaleString(undefined,{maximumFractionDigits:0})}`, sub:`$1M target · ${(Number(s.volume)/1_000_000*100).toFixed(2)}%`, color:'text-sky-400'},
    {label:'CPM', value:`$${Number(p.cpm??s.cpm).toFixed(2)}/M`, sub:`Per $1M volume`, color:'text-sky-300'},
    {label:'Net PnL', value:`${Number(p.net)>=0?'+':''}$${Number(p.net).toFixed(3)}`, sub:`${Number(p.realized).toFixed(3)} real`, color: Number(p.net)>=0?'text-emerald-400':'text-red-400'},
  ]
  return (
    <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
      {cards.map(c=>(
        <div key={c.label} className="bg-slate-900 border border-slate-800 rounded-2xl p-4">
          <div className="text-xs tracking-widest text-slate-400 uppercase">{c.label}</div>
          <div className={`text-xl md:text-2xl font-bold mt-1 ${c.color}`}>{c.value}</div>
          <div className="text-xs text-slate-500 mt-1">{c.sub}</div>
        </div>
      ))}
    </div>
  )
}

export default function Dashboard() {
  return (
    <div className="min-h-screen bg-[#0a0e1a] p-4 md:p-6 max-w-6xl mx-auto space-y-4">
      <header className="flex items-center justify-between">
        <h1 className="text-xl font-bold tracking-tight">Arcus Market Maker</h1>
        <div className="flex items-center gap-2"><ExecutionStatus /><TradingModeBadge /></div>
      </header>
      <ControlPanel />
      <MetricCards />
      <TradeHistory />
      <div className="text-xs text-slate-600 text-center">ALL PAIRS auto · Pure Limit ALO 0% taker · Millisecond · Live Arcus feeds · Exact sub-cent WIN <span className="text-emerald-400">+0.015</span> / LOSS <span className="text-red-400">-0.006</span></div>
    </div>
  )
}
