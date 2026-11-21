import { Play, Square, RotateCcw } from 'lucide-react'
import { api } from '../services/api'

export default function SimControls({ sim, onChange }) {
  const running = sim?.running
  const call = (fn) => () => fn().then(onChange).catch(() => {})
  const pct = sim ? Math.round((sim.tick / sim.total_ticks) * 100) : 0
  const btn = 'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs border focus:outline-none focus-visible:ring-2 focus-visible:ring-signal disabled:opacity-40'
  return (
    <div className="flex flex-wrap items-center gap-3">
      <button className={`${btn} bg-signal text-ink border-signal font-medium`} disabled={running} onClick={call(api.startSimulation)}>
        <Play size={14} />Start simulation
      </button>
      <button className={`${btn} border-line text-slate-200 hover:bg-raised`} disabled={!running} onClick={call(api.stopSimulation)}>
        <Square size={14} />Stop
      </button>
      <button className={`${btn} border-line text-slate-200 hover:bg-raised`} disabled={running} onClick={call(api.resetDemo)}>
        <RotateCcw size={14} />Reset demo
      </button>
      <div className="text-xs text-mute min-w-40">
        {running ? <>Running · simulated clock <span className="font-mono text-slate-200">{sim.sim_time_ist} IST</span></>
          : sim?.state === 'completed' ? 'Simulation complete' : sim?.state === 'stopped' ? 'Stopped' : 'Simulated devices, real detection engine'}
        {(running || sim?.state === 'completed') && (
          <div className="h-1 bg-line rounded mt-1.5"><div className="h-1 bg-signal rounded transition-all" style={{ width: `${pct}%` }} /></div>
        )}
      </div>
    </div>
  )
}
