import { useEffect, useState } from 'react'

export default function TradeHistory(){
  const [trades,setTrades]=useState<any[]>([])
  const [err,setErr]=useState<string|null>(null)
  const load=async()=>{
    try{ const r=await fetch('/api/trades/history').then(r=>r.json()); setTrades(r.trades||[]) }catch(e:any){ setErr(String(e)) }
  }
  useEffect(()=>{ load(); const id=setInterval(load,800); return()=>clearInterval(id)},[])
  if(err) return <div className="p-4 bg-red-900/30 border border-red-800 rounded-xl text-xs">{err}</div>
  return (
    <div className="p-5 bg-slate-900 border border-slate-800 rounded-2xl overflow-auto">
      <div className="text-sm font-semibold">Live Trade History · Exact Micro PnL <span className="text-slate-500 font-normal">({trades.length})</span> <span className="text-xs ml-2 text-slate-400">Entry → Exit · Duration · Net (red = sub-cent loss)</span></div>
      <table className="w-full text-xs mt-3">
        <thead className="text-slate-400"><tr><th className="text-left p-1">Time</th><th>Market</th><th>Side</th><th>Entry</th><th>Exit</th><th>Qty</th><th>Duration</th><th>Net PnL</th></tr></thead>
        <tbody>
          {trades.slice(0,50).map((t:any,i:number)=>(
            <tr key={i} className={`border-t border-slate-800 ${t.is_loss?'bg-red-950/20': t.is_win?'bg-emerald-950/20':''}`}>
              <td className="p-1 font-mono text-[10px]">{new Date(t.exit_ts/1_000_000).toLocaleTimeString()}</td>
              <td className="text-center">{t.market}</td>
              <td className={`text-center ${t.side==='buy'?'text-emerald-400':'text-red-400'}`}>{t.side}</td>
              <td className="text-right font-mono">{Number(t.entry_price).toFixed(2)}</td>
              <td className="text-right font-mono">{Number(t.exit_price).toFixed(2)}</td>
              <td className="text-right">{Number(t.quantity).toFixed(6)}</td>
              <td className="text-right">{t.duration_ms}ms</td>
              <td className={`text-right font-bold ${t.net_pnl<0?'text-red-400':'text-emerald-400'}`}>{t.net_pnl>=0?'+':''}{Number(t.net_pnl).toFixed(3)}</td>
            </tr>
          ))}
          {trades.length===0 && <tr><td colSpan={8} className="p-4 text-center text-slate-500">No closed trades yet — start bot, micro TP $0.01-0.02 / SL &lt;$0.01 will stream here</td></tr>}
        </tbody>
      </table>
      {trades.some(t=>t.is_loss) && <div className="text-xs text-red-400 mt-2">Exact sub-cent losses displayed in red, e.g. {trades.find(t=>t.is_loss)?.net_pnl_str} — strict &lt;$0.01 SL enforced</div>}
    </div>
  )
}
