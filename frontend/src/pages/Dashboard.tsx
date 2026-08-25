import { useEffect, useState } from 'react'
import StatusCard from '../components/StatusCard'
import TradingModeBadge from '../components/TradingModeBadge'
import VolumeCard from '../components/VolumeCard'
import PnLCards from '../components/PnLCards'
import RiskDashboard from '../components/RiskDashboard'
import OrderTable from '../components/OrderTable'
import FillTable from '../components/FillTable'
import BotControls from '../components/BotControls'
import DashboardCharts from '../charts/DashboardCharts'
import Settings from './Settings'
import { api } from '../services/api'

function MainStats(){
  const [s,setS]=useState<any>(null)
  useEffect(()=>{
    const f=async()=>{ try{setS(await api.analyticsStatus())}catch{}}
    f(); const id=setInterval(f,2000); return()=>clearInterval(id)
  },[])
  if(!s) return <div className="p-5 bg-slate-900 border border-slate-800 rounded-2xl">Loading…</div>
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      {[
        ['Market', s.market],['Bid', s.bid? Number(s.bid).toFixed(2):'—'],['Ask', s.ask? Number(s.ask).toFixed(2):'—'],['Mid', s.mid? Number(s.mid).toFixed(2):'—'],
        ['Spread', s.spread? Number(s.spread).toFixed(4):'—'],['Spread bps', s.spread_bps? Number(s.spread_bps).toFixed(1):'—'],['Inventory', Number(s.inventory).toFixed(4)],['Exposure', `$${Number(s.exposure).toFixed(2)}`],
        ['Open Orders', String(s.open_orders)],['Volume', `$${Number(s.volume).toFixed(2)}`],['PnL', `$${Number(s.net_pnl).toFixed(2)}`],['Fees', `$${Number(s.fees).toFixed(4)}`],
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
        <h1 className="text-2xl font-bold tracking-tight">Arcus Market Maker <span className="text-slate-500 font-normal">· Legit liquidity</span></h1>
        <TradingModeBadge />
      </header>

      <BotControls />
      <MainStats />
      <VolumeCard />
      <PnLCards />
      <DashboardCharts />
      <RiskDashboard />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <OrderTable />
        <FillTable />
      </div>
      <Settings />
      <div className="text-xs text-slate-500 text-center">PAPER default · LIVE gated · No wash trading · No fake volume · DMS + Emergency Stop</div>
    </div>
  )
}
