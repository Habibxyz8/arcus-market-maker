import { useEffect, useState } from 'react'

export default function TradeHistory(){
  const [trades,setTrades]=useState<any[]>([])
  const load=async()=>{
    try{ const r=await fetch('/api/trades/history').then(r=>r.json()); setTrades(r.trades||[]) }catch{}
  }
  useEffect(()=>{ load(); const id=setInterval(load,600); return()=>clearInterval(id)},[])
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden">
      <div className="px-5 py-3 border-b border-slate-800 flex items-center justify-between">
        <div className="text-sm font-semibold">Live Trades <span className="text-slate-500 font-normal ml-2">{trades.length} fills</span></div>
        <div className="text-xs text-slate-500">Micro TP $0.01-0.02 · SL &lt;$0.01 · exact sub-cent</div>
      </div>
      <div className="overflow-auto max-h-[380px]">
        <table className="w-full text-sm">
          <thead className="text-xs text-slate-400 sticky top-0 bg-slate-900">
            <tr><th className="text-left px-4 py-2">Pair</th><th className="text-left px-3 py-2">Side</th><th className="text-right px-3 py-2">Entry / Exit</th><th className="text-right px-4 py-2">Net PnL</th><th className="text-center px-4 py-2">Status</th></tr>
          </thead>
          <tbody className="divide-y divide-slate-800">
            {trades.slice(0,40).map((t:any,i:number)=>(
              <tr key={i} className={t.is_loss?'bg-red-950/15': t.is_win?'bg-emerald-950/15':''}>
                <td className="px-4 py-2 font-medium">{t.market}</td>
                <td className={`px-3 py-2 font-bold ${t.side==='buy'?'text-emerald-400':'text-red-400'}`}>{t.side.toUpperCase()}</td>
                <td className="px-3 py-2 text-right font-mono text-xs">{Number(t.entry_price).toFixed(2)} → {Number(t.exit_price).toFixed(2)} <span className="text-slate-500">· {t.duration_ms}ms</span></td>
                <td className={`px-4 py-2 text-right font-mono font-bold ${t.net_pnl<0?'text-red-400':'text-emerald-400'}`}>{t.net_pnl>=0?'+':''}{Number(t.net_pnl).toFixed(3)}</td>
                <td className="px-4 py-2 text-center"><span className={`text-xs px-2 py-1 rounded-full font-bold ${t.is_loss?'bg-red-900 text-red-200': t.is_win?'bg-emerald-900 text-emerald-200':'bg-slate-800 text-slate-300'}`}>{t.is_loss?'LOSS':'WIN'}</span></td>
              </tr>
            ))}
            {trades.length===0 && <tr><td colSpan={5} className="px-4 py-8 text-center text-slate-500 text-sm">No trades yet — press START for continuous HFT loop</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  )
}
