import { useEffect, useState } from 'react'
import { api } from '../services/api'

export default function TradingControls(){
  const [s,setS]=useState<any>(null)
  const [customUsd,setCustomUsd]=useState<string>('')
  const [msg,setMsg]=useState<string|null>(null)

  const load=async()=>{ try{ setS(await api.getSettings()) }catch{} }
  useEffect(()=>{ load() },[])
  if(!s) return <div className="p-5 bg-slate-900 border border-slate-800 rounded-2xl">Loading controls…</div>

  const applyPreset=async(preset:string)=>{
    await api.updateSettings({strategy_preset:preset}); await load(); setMsg(`Preset ${preset} applied`); setTimeout(()=>setMsg(null),2000)
  }
  const applyCustomUsd=async()=>{
    const v=parseFloat(customUsd)
    if(isNaN(v)||v<=0){ setMsg('Enter valid USD like 50'); return }
    await api.updateSettings({order_size_usd:v}); await load(); setMsg(`Order size $${v} set`); setCustomUsd(''); setTimeout(()=>setMsg(null),2000)
  }
  const setMarket=async(m:string)=>{ await api.selectMarket(m); await load() }

  const presets = s.presets || {}
  return (
    <div className="p-5 bg-slate-900 border border-slate-800 rounded-2xl space-y-4">
      <div className="text-sm font-semibold">Strategy & Order Size · 10x leverage mandatory · TP $0.01-0.02 · SL &lt;$0.01 strict</div>

      <div className="flex flex-wrap gap-2">
        {Object.keys(presets).filter(k=>k!=='custom').map(k=>(
          <button key={k} onClick={()=>applyPreset(k)} className={`px-3 py-1.5 rounded-lg text-xs font-bold border ${s.strategy_preset===k?'bg-sky-600 border-sky-500 text-white':'bg-slate-800 border-slate-700 text-slate-300 hover:bg-slate-700'}`}>
            {k.toUpperCase()} <span className="font-normal opacity-70">{presets[k]?.desc}</span>
          </button>
        ))}
        <button onClick={()=>applyPreset('custom')} className={`px-3 py-1.5 rounded-lg text-xs font-bold border ${s.strategy_preset==='custom'?'bg-amber-600 border-amber-500':'bg-slate-800 border-slate-700'}`}>CUSTOM</button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-slate-800/50 p-3 rounded-xl border border-slate-700">
          <div className="text-xs text-slate-400">Custom Order Size (USD)</div>
          <div className="flex gap-2 mt-2">
            <input value={customUsd} onChange={e=>setCustomUsd(e.target.value)} placeholder={`Current $${s.order_size_usd}`} className="flex-1 bg-slate-900 border border-slate-700 rounded px-2 py-1.5 text-sm" />
            <button onClick={applyCustomUsd} className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 rounded text-sm font-semibold">Set</button>
          </div>
          <div className="flex gap-2 mt-2">
            {[50,60,70].map(v=>(
              <button key={v} onClick={async()=>{await api.updateSettings({order_size_usd:v}); await load()}} className="flex-1 py-1 bg-slate-700 hover:bg-slate-600 rounded text-xs">${v}</button>
            ))}
          </div>
          <div className="text-xs text-slate-500 mt-1">Any size allowed · With 10x, $70 uses $7 margin of $100</div>
        </div>

        <div className="bg-slate-800/50 p-3 rounded-xl border border-slate-700">
          <div className="text-xs text-slate-400">Multi-Pair</div>
          <select value={s.market} onChange={e=>setMarket(e.target.value)} className="w-full mt-2 bg-slate-900 border border-slate-700 rounded px-2 py-1.5 text-sm">
            {(s.supported_markets||[]).map((m:string)=><option key={m} value={m}>{m}</option>)}
          </select>
          <div className="text-xs text-slate-500 mt-1">Switches synthetic PAPER feed instantly · Quote loop restarts</div>
        </div>

        <div className="bg-slate-800/50 p-3 rounded-xl border border-slate-700">
          <div className="text-xs text-slate-400">Micro Risk</div>
          <div className="text-xs mt-2">Leverage <b className="text-sky-400">10x mandatory</b> · TP ${Number(s.take_profit_usd).toFixed(3)} · SL ${Number(s.stop_loss_usd).toFixed(3)} &lt;$0.01 strict</div>
          <div className="text-xs text-slate-500 mt-1">Sub-cent SL eliminates inventory/adverse loss each cycle</div>
          <div className="flex gap-2 mt-2">
            <label className="text-xs flex-1">TP <input type="number" step="0.001" min="0.01" max="0.02" value={s.take_profit_usd} onChange={async e=>{await api.updateSettings({take_profit_usd:parseFloat(e.target.value)}); await load()}} className="w-full mt-1 bg-slate-900 border border-slate-700 rounded px-1 py-1 text-xs" /></label>
            <label className="text-xs flex-1">SL <input type="number" step="0.001" min="0.001" max="0.009" value={s.stop_loss_usd} onChange={async e=>{await api.updateSettings({stop_loss_usd:parseFloat(e.target.value)}); await load()}} className="w-full mt-1 bg-slate-900 border border-slate-700 rounded px-1 py-1 text-xs" /></label>
          </div>
        </div>
      </div>
      {msg && <div className="text-xs text-emerald-400">{msg}</div>}
      <div className="text-xs text-slate-400">Current: {s.market} · ${s.order_size_usd} (approx {(s.order_size).toFixed(6)} base) · {s.strategy_preset} · {s.leverage}x</div>
    </div>
  )
}
