import { useEffect, useState } from 'react'
import TradingModeBadge from '../components/TradingModeBadge'
import VolumeCard from '../components/VolumeCard'
import PnLCards from '../components/PnLCards'
import RiskDashboard from '../components/RiskDashboard'
import OrderTable from '../components/OrderTable'
import FillTable from '../components/FillTable'
import BotControls from '../components/BotControls'
import DashboardCharts from '../charts/DashboardCharts'
import Settings from './Settings'
import TradingControls from '../components/TradingControls'
import BalanceMetrics from '../components/BalanceMetrics'
import TradeHistory from '../components/TradeHistory'
import { api } from '../services/api'

function MainStats(){
  const [s,setS]=useState<any>(null)
  useEffect(()=>{
    // Live millisecond feed: poll 300ms or WS push (WS every 200ms from backend)
    let ws: WebSocket | null = null
    try{
      const proto = location.protocol==='https:'?'wss:':'ws:'
      ws = new WebSocket(`${proto}//${location.host}/api/ws/dashboard`)
      ws.onmessage = e=>{ try{ const j=JSON.parse(e.data); if(j.mid) setS(j) }catch{} }
    }catch{}
    const f=async()=>{ try{setS(await api.analyticsStatus())}catch{}}
    f(); const id=setInterval(f,350); return()=>{clearInterval(id); try{ws?.close()}catch{}}
  },[])
  if(!s) return <div className="p-5 bg-slate-900 border border-slate-800 rounded-2xl">Loading live BID/ASK/MID…</div>
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      {[
        ['Market', s.market],['BID', s.bid? Number(s.bid).toFixed(2):'—'],['ASK', s.ask? Number(s.ask).toFixed(2):'—'],['MID', s.mid? Number(s.mid).toFixed(2):'—'],
        ['Spread', s.spread? Number(s.spread).toFixed(4):'—'],['Spread bps', s.spread_bps? Number(s.spread_bps).toFixed(1):'—'],['Inventory', Number(s.inventory).toFixed(6)],['Exposure', `$${Number(s.exposure).toFixed(2)}`],
        ['Open Orders (ALO maker)', String(s.open_orders)],['Volume', `$${Number(s.volume).toFixed(2)}`],['Net PnL', `$${Number(s.net_pnl).toFixed(3)}`],['Fees (maker 0%)', `$${Number(s.fees).toFixed(4)}`],
      ].map(([k,v])=>(
        <div key={k} className="p-3 bg-slate-900 border border-slate-800 rounded-xl"><div className="text-xs text-slate-400 uppercase tracking-widest">{k}</div><div className="text-sm font-bold mt-1">{String(v)}</div></div>
      ))}
    </div>
  )
}

export default function Dashboard() {
  return (
    <div className="min-h-screen p-6 max-w-7xl mx-auto space-y-6">
      <header className="flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight">Arcus Market Maker <span className="text-slate-500 font-normal">· Micro TP/SL</span></h1>
        <TradingModeBadge />
      </header>

      <BotControls />
      <TradingControls />
      <BalanceMetrics />
      <MainStats />
      <VolumeCard />
      <PnLCards />
      <TradeHistory />
      <DashboardCharts />
      <RiskDashboard />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <OrderTable />
        <FillTable />
      </div>
      <Settings />
      <div className="text-xs text-slate-500 text-center">Pure Limit ALO (maker) · Millisecond HFT · Live Arcus BID/ASK/MID · Exact sub-cent loss · Margin × Leverage (Arcus max per pair)</div>
    </div>
  )
}
