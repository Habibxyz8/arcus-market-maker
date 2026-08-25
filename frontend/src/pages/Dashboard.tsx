import StatusCard from '../components/StatusCard'
import TradingModeBadge from '../components/TradingModeBadge'

export default function Dashboard() {
  return (
    <div className="min-h-screen p-6 max-w-7xl mx-auto space-y-6">
      <header className="flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight">Arcus Market Maker <span className="text-slate-500 font-normal">· Phase 4</span></h1>
        <TradingModeBadge />
      </header>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatusCard />
        <div className="p-5 bg-slate-900 border border-slate-800 rounded-2xl">
          <div className="text-xs uppercase tracking-widest text-slate-400">$1M Target</div>
          <div className="text-2xl font-bold mt-1">— <span className="text-slate-500 text-base font-normal">(Phase 24)</span></div>
          <div className="text-sm text-slate-400 mt-1">Volume tracking wired in Phases 21-25</div>
        </div>
        <div className="p-5 bg-slate-900 border border-slate-800 rounded-2xl">
          <div className="text-xs uppercase tracking-widest text-slate-400">PnL</div>
          <div className="text-2xl font-bold mt-1">— <span className="text-slate-500 text-base font-normal">(Phase 25)</span></div>
          <div className="text-sm text-slate-400 mt-1">Gross / Fees / Net (Phase 13-15)</div>
        </div>
      </div>

      <div className="p-5 bg-slate-900 border border-slate-800 rounded-2xl">
        <div className="text-sm font-semibold">Next steps</div>
        <ul className="list-disc ml-5 mt-2 text-sm text-slate-300 space-y-1">
          <li>Backend at <code className="bg-slate-800 px-1 rounded">http://localhost:8000</code> — <code>/api/health</code>, <code>/api/bot/*</code>, <code>/api/ws/dashboard</code></li>
          <li>Phases 6-7 Arcus REST/WS client (official docs only), Phases 8-20 strategy/risk</li>
          <li>Dark dashboard phases 26-34 expand after market data engine</li>
        </ul>
      </div>
    </div>
  )
}
