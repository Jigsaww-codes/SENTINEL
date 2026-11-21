import { useCallback, useState } from 'react'
import { api } from '../services/api'
import useApi from '../hooks/useApi'
import AlertCard from '../components/AlertCard'

const FILTERS = [['open', 'Awaiting verification'], ['closed', 'Closed'], ['all', 'All']]

export default function Alerts({ refreshKey, onViewMap, focus }) {
  const { data: alerts, error, reload } = useApi(useCallback(() => api.alerts(), []), refreshKey, [])
  const [filter, setFilter] = useState('open')
  const update = async (id, body) => { await api.updateAlert(id, body); reload() }
  const closed = s => s === 'DISMISSED' || s === 'RESOLVED'
  const shown = alerts
    .filter(a => filter === 'all' || (filter === 'closed') === closed(a.status))
    .sort((a, b) => (closed(a.status) - closed(b.status)) || b.risk_score - a.risk_score)

  return (
    <div className="p-6 space-y-5 max-w-5xl">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-white">Emergency alerts</h1>
          <p className="text-mute text-sm mt-1">Patterns that need a person to look. SENTINEL never dispatches or acts on its own.</p>
        </div>
        <div className="flex gap-1 bg-panel border border-line rounded-md p-1">
          {FILTERS.map(([k, label]) => (
            <button key={k} onClick={() => setFilter(k)}
              className={`px-3 py-1.5 rounded text-xs focus:outline-none focus-visible:ring-2 focus-visible:ring-signal ${filter === k ? 'bg-raised text-white' : 'text-mute hover:text-slate-200'}`}>
              {label}
            </button>
          ))}
        </div>
      </header>
      {error && <div className="text-high text-sm">Could not load alerts: {error}</div>}
      {shown.length === 0 && !error && (
        <div className="bg-panel border border-dashed border-line rounded-lg p-8 text-mute text-sm">
          {filter === 'open' ? 'No alerts are waiting for verification. Start the simulation to generate location updates.' : 'Nothing to show here yet.'}
        </div>
      )}
      <div className="space-y-4">
        {shown.map(a => <AlertCard key={a.alert_id} alert={a} onViewMap={onViewMap} onUpdate={update} selected={focus?.alert_id === a.alert_id} />)}
      </div>
    </div>
  )
}
