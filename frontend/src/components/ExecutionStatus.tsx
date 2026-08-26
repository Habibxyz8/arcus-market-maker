import { useEffect, useState } from 'react'

export default function ExecutionStatus(){
  const [status,setStatus]=useState<string>('IDLE')
  const [state,setState]=useState<string>('STOPPED')
  useEffect(()=>{
    let ws: WebSocket | null = null
    const connect=()=>{
      try{
        const proto = location.protocol==='https:'?'wss:':'ws:'
        // Use same host, rely on vite proxy for /api/ws
        ws = new WebSocket(`${proto}//${location.host}/api/ws/dashboard`)
        ws.onmessage=e=>{
          try{
            const j=JSON.parse(e.data)
            if(j.execution_status) setStatus(j.execution_status)
            if(j.state) setState(j.state)
          }catch{}
        }
        ws.onclose=()=>{ setTimeout(connect,1500) }
      }catch{}
    }
    connect()
    // fallback poll
    const id=setInterval(async()=>{
      try{
        const r=await fetch('/api/analytics/status').then(r=>r.json())
        if(r.execution_status) setStatus(r.execution_status)
        if(r.state) setState(r.state)
      }catch{}
    },800)
    return()=>{ try{ws?.close()}catch{}; clearInterval(id)}
  },[])
  const isRunning=state==='RUNNING'
  const color = !isRunning ? 'bg-slate-800 text-slate-400' :
                status.includes('FILLED') ? 'bg-emerald-900 text-emerald-200 border-emerald-700' :
                status.includes('RE-OPENING') ? 'bg-sky-900 text-sky-200 border-sky-700' :
                status.includes('PLACING') ? 'bg-amber-900 text-amber-200 border-amber-700' :
                'bg-slate-800 text-slate-300'
  return (
    <div className={`px-4 py-2 rounded-xl border text-xs font-mono flex items-center gap-2 ${color} border-slate-700`}>
      <span className={`w-2 h-2 rounded-full ${isRunning?'bg-emerald-400 animate-pulse':'bg-slate-500'}`}></span>
      <span className="font-bold">{state}</span>
      <span className="opacity-60">·</span>
      <span className="truncate">{status}</span>
    </div>
  )
}
