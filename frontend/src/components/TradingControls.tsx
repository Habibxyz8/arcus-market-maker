import { useEffect, useState } from 'react'
import { api } from '../services/api'

export default function TradingControls(){
  const [s,setS]=useState<any>(null)
  const [customUsd,setCustomUsd]=useState<string>('')
  const [margin,setMargin]=useState<string>('')
  const [lev,setLev]=useState<string>('')
  const [msg,setMsg]=useState<string|null>(null)

  const load=async()=>{
    try{
      const j=await api.getSettings()
      setS(j)
      // fetch limits for max leverage display
      try{ const lim=await fetch('/api/markets/limits').then(r=>r.json()); if(lim.limits) j._limits=lim.limits }catch{}
      setS({...j})
    }catch{}
  }
  useEffect(()=>{ load() },[])
  if(!s) return <div className="p-5 bg-slate-900 border border-slate-800 rounded-2xl">Loading controls…</div>

  const maxLev = s.max_leverage_for_pair || 10
  const tick = s.tickSize || '0.1'
  const applyPreset=async(preset:string)=>{
    await api.updateSettings({strategy_preset:preset}); await load(); setMsg(`Preset ${preset} applied`); setTimeout(()=>setMsg(null),2000)
  }
  const applyMarginLev=async()=>{
    const m=parseFloat(margin), l=parseInt(lev)
    if(margin && (isNaN(m)||m<1||m>1000)){ setMsg('Margin $1-1000'); return }
    if(lev && (isNaN(l)||l<1||l>maxLev)){ setMsg(`Leverage 1-${maxLev}x for ${s.market}`); return }
    const p:any={}
    if(margin) p.margin_usd=m
    if(lev) p.leverage=l
    if(Object.keys(p).length===0){ setMsg('Enter margin or leverage'); return }
    await api.updateSettings(p); await load(); setMsg(`Margin $${s.margin_usd} x${s.leverage} → Position $${s.position_notional?.toFixed? s.position_notional.toFixed(0): Math.round(s.margin_usd*s.leverage)}`); setMargin(''); setLev(''); setTimeout(()=>setMsg(null),2500)
  }
  const applyCustomUsd=async()=>{
    const v=parseFloat(customUsd)
    if(isNaN(v)||v<=0){ setMsg('Enter valid notional like 50'); return }
    await api.updateSettings({order_size_usd:v}); await load(); setMsg(`Position size $${v} set`); setCustomUsd(''); setTimeout(()=>setMsg(null),2000)
  }
  const setMarket=async(m:string)=>{ await api.selectMarket(m); await load() }
  const presets = s.presets || {}
  const position = s.position_notional || (s.margin_usd * s.leverage)

  return (
    <div className="p-5 bg-slate-900 border border-slate-800 rounded-2xl space-y-4">
      <div className="text-sm font-semibold">Dynamic Margin & Leverage · Arcus Pair Limits · Pure Limit ALO</div>
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
          <div className="text-xs text-slate-400">Margin ($1-$100+) × Leverage (max {maxLev}x for {s.market})</div>
          <div className="flex gap-2 mt-2">
            <input value={margin} onChange={e=>setMargin(e.target.value)} placeholder={`Margin $${s.margin_usd}`} className="flex-1 bg-slate-900 border border-slate-700 rounded px-2 py-1.5 text-sm" />
            <input value={lev} onChange={e=>setLev(e.target.value)} placeholder={`${s.leverage}x`} className="w-20 bg-slate-900 border border-slate-700 rounded px-2 py-1.5 text-sm" />
            <button onClick={applyMarginLev} className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 rounded text-sm font-semibold">Set</button>
          </div>
          <div className="text-xs mt-2">Position Size: <b className="text-sky-400">${Number(position).toFixed(0)}</b> = ${s.margin_usd} × {s.leverage}x · Tick {tick} · Used margin streamed from open limits</div>
          <div className="text-xs text-slate-500 mt-1">Arcus max {maxLev}x enforced per pair (crypto 15-20x, stocks 5x)</div>
        </div>

        <div className="bg-slate-800/50 p-3 rounded-xl border border-slate-700">
          <div className="text-xs text-slate-400">Custom Notional (alternative)</div>
          <div className="flex gap-2 mt-2">
            <input value={customUsd} onChange={e=>setCustomUsd(e.target.value)} placeholder={`$${s.order_size_usd}`} className="flex-1 bg-slate-900 border border-slate-700 rounded px-2 py-1.5 text-sm" />
            <button onClick={applyCustomUsd} className="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 rounded text-sm">Set</button>
          </div>
          <div className="flex gap-2 mt-2">
            {[50,60,70].map(v=>(
              <button key={v} onClick={async()=>{await api.updateSettings({order_size_usd:v}); await load()}} className="flex-1 py-1 bg-slate-700 hover:bg-slate-600 rounded text-xs">${v}</button>
            ))}
          </div>
        </div>

        <div className="bg-slate-800/50 p-3 rounded-xl border border-slate-700">
          <div className="text-xs text-slate-400">Live Pair & Micro Risk</div>
          <select value={s.market} onChange={e=>setMarket(e.target.value)} className="w-full mt-2 bg-slate-900 border border-slate-700 rounded px-2 py-1.5 text-sm">
            {(s.supported_markets||[]).map((m:string)=><option key={m} value={m}>{m} {m===s.market?`· max ${maxLev}x`:''}</option>)}
          </select>
          <div className="text-xs mt-2">TP ${Number(s.take_profit_usd).toFixed(3)} · SL ${Number(s.stop_loss_usd).toFixed(3)} &lt;$0.01 strict</div>
          <div className="flex gap-2 mt-2">
            <label className="text-xs flex-1">TP <input type="number" step="0.001" min="0.01" max="0.02" value={s.take_profit_usd} onChange={async e=>{await api.updateSettings({take_profit_usd:parseFloat(e.target.value)}); await load()}} className="w-full mt-1 bg-slate-900 border border-slate-700 rounded px-1 py-1 text-xs" /></label>
            <label className="text-xs flex-1">SL <input type="number" step="0.001" min="0.001" max="0.009" value={s.stop_loss_usd} onChange={async e=>{await api.updateSettings({stop_loss_usd:parseFloat(e.target.value)}); await load()}} className="w-full mt-1 bg-slate-900 border border-slate-700 rounded px-1 py-1 text-xs" /></label>
          </div>
        </div>
      </div>
      {msg && <div className="text-xs text-emerald-400">{msg}</div>}
    </div>
  )
}
