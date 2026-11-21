import { useCallback } from 'react'
import { api } from '../services/api'
import useApi from '../hooks/useApi'
import RiskBadge from '../components/RiskBadge'
import { fmtDuration } from '../services/format'

const NAMES = { stationary_minutes: 'stationary time', movement_frequency: 'movement', isolation_score: 'isolation',
  road_distance_m: 'road distance', incident_score: 'incident context', time_score: 'time of day' }

export default function Anomaly({ refreshKey }) {
  const { data: an } = useApi(useCallback(() => api.analytics(), []), refreshKey)
  const { data: devices } = useApi(useCallback(() => api.devices(), []), refreshKey, [])
  const by = an?.latest_by_device || {}
  return (
    <div className="p-6 space-y-5 max-w-6xl">
      <header><h1 className="text-2xl font-semibold text-white">Anomaly detection</h1>
        <p className="text-mute text-sm mt-1">Per-device view: only devices that stay put past the threshold are scored. Moving devices are not.</p></header>
      {devices.length === 0 && <div className="bg-panel border border-dashed border-line rounded-lg p-8 text-sm text-mute">No devices yet. Start the simulation.</div>}
      <div className="grid md:grid-cols-2 gap-4">
        {devices.map(d => {
          const v = by[d.device_id], b = v?.breakdown, top = Object.entries(v?.feature_contributions || {}).filter(([, p]) => p > 0).sort((x, y) => y[1] - x[1]).slice(0, 3)
          return (
            <article key={d.device_id} className="bg-panel border border-line rounded-lg p-4 space-y-3">
              <div className="flex justify-between"><span className="font-mono text-white">{d.device_id}</span><RiskBadge level={d.risk_level} score={d.risk_score || null} /></div>
              <div className="text-sm text-slate-300">{d.stationary_minutes > 0 ? `Stationary for ${fmtDuration(d.stationary_minutes)}` : 'Moving'}</div>
              {b ? (<>
                <div><div className="flex justify-between text-xs text-mute mb-1"><span>Isolation Forest anomaly score</span><span className="font-mono text-slate-200">{b.M}</span></div>
                  <div className="h-2 bg-line rounded"><div className="h-2 rounded bg-ok" style={{ width: `${b.M}%` }} /></div></div>
                <p className="text-xs text-mute">Driven mostly by: {top.map(([f, p]) => `${NAMES[f]} (${p}%)`).join(', ') || '–'}</p>
                <ul className="list-disc pl-5 text-xs text-slate-300 space-y-0.5 marker:text-mute">{v.reasons.map((r, i) => <li key={i}>{r}</li>)}</ul>
              </>) : <p className="text-xs text-mute">Not scored: below the stationary threshold.</p>}
            </article>)
        })}
      </div>
    </div>
  )
}
