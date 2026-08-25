import { useEffect, useState } from 'react'
import { api } from '../services/api'

export default function Settings(){
  const [s,setS]=useState<any>(null)
  const [msg,setMsg]=useState<string|null>(null)
  useEffect(()=>{ api.getSettings().then(setS).catch(()=>{})},[])
  if(!s) return <div className="p-5 bg-slate-900 rounded-2xl">Loading settings…</div>
  const fields: [string,string][]=[
    ['market','Market'],['order_size','Order size'],['max_order_size','Max order size'],['bid_spread_bps','Bid spread (bps)'],['ask_spread_bps','Ask spread (bps)'],
    ['quote_refresh_interval_ms','Refresh ms'],['max_inventory','Max inventory'],['max_exposure','Max exposure'],['max_daily_loss','Max daily loss'],['max_open_orders','Max open orders'],
    ['max_order_age_sec','Max order age sec'],['min_expected_profit','Min expected profit'],['min_expected_edge_bps','Min edge bps'],['inventory_skew_factor','Inventory skew'],['maker_fee_bps','Maker fee bps'],['dead_mans_switch_timeout_sec','DMS timeout sec'],
  ]
  return (
    <div className="p-5 bg-slate-900 border border-slate-800 rounded-2xl">
      <div className="text-sm font-semibold">Settings (Phase 34) - TRADING_MODE via .env only</div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
        {fields.map(([k,label])=>(
          <label key={k} className="text-xs text-slate-400">{label}
            <input className="w-full mt-1 bg-slate-800 border border-slate-700 rounded px-2 py-1.5 text-sm text-slate-100" value={String(s[k]??'')} onChange={e=>setS({...s, [k]: isNaN(Number(e.target.value))? e.target.value : Number(e.target.value)})} />
          </label>
        ))}
      </div>
      <button onClick={async()=>{ await api.updateSettings(s); setMsg('Saved'); setTimeout(()=>setMsg(null),2000)}} className="mt-4 px-4 py-2 bg-sky-600 hover:bg-sky-500 rounded-lg text-sm font-semibold">Save</button>
      {msg && <span className="ml-3 text-sm text-emerald-400">{msg}</span>}
      <div className="text-xs text-slate-500 mt-3">PAPER volume never mixes with LIVE. Credentials only via .env (ARCUS_API_KEY/SECRET).</div>
    </div>
  )
}
