import { useCallback, useState } from 'react'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api } from '../services/api'
import useApi from '../hooks/useApi'
import BreakdownBar from '../components/BreakdownBar'
import RiskBadge from '../components/RiskBadge'
import Badge from '../components/Badge'

const NAMES = { stationary_minutes: 'Stationary time', movement_frequency: 'Movement frequency', isolation_score: 'Isolation',
  road_distance_m: 'Distance from roads', incident_score: 'Incident context', time_score: 'Time of day' }

export default function Analytics({ refreshKey }) {
  const { data: a, error } = useApi(useCallback(() => api.analytics(), []), refreshKey)
  const [sel, setSel] = useState(null)
  if (error) return <div className="p-6 text-high text-sm">Could not load analytics: {error}</div>
  if (!a) return <div className="p-6 text-mute text-sm">Loading…</div>
  const devs = Object.entries(a.latest_by_device).filter(([, v]) => v.breakdown)
  const cur = devs.find(([k]) => k === sel) || devs[devs.length - 1]
  const passed = a.false_positive_tests.filter(t => t.passed).length
  const chart = a.feature_contributions.map(f => ({ ...f, name: NAMES[f.feature] || f.feature }))

  return (
    <div className="p-6 space-y-6 max-w-6xl">
      <header><h1 className="text-2xl font-semibold text-white">AI analytics</h1>
        <p className="text-mute text-sm mt-1">How the model and the risk score reach their conclusions.</p></header>

      <div className="grid md:grid-cols-3 gap-4">
        <div className="bg-panel border border-line rounded-lg p-4"><div className="text-sm text-mute">Model</div>
          <div className="text-white mt-1">{a.model.name}</div>
          <div className="mt-2"><Badge kind={a.model.status === 'trained' ? 'ACTIVE' : 'STANDBY'}>{a.model.status}</Badge></div>
          <p className="text-xs text-mute mt-2">{a.model.n_estimators} trees · {a.model.training_rows} rows · trained on {a.model.training_data.toLowerCase()}</p></div>
        <div className="bg-panel border border-line rounded-lg p-4"><div className="text-sm text-mute">Anomalies flagged now</div><div className="text-3xl font-semibold text-review mt-1">{a.anomalies}</div></div>
        <div className="bg-panel border border-line rounded-lg p-4"><div className="text-sm text-mute">False-positive tests</div>
          <div className={`text-3xl font-semibold mt-1 ${passed === a.false_positive_tests.length ? 'text-ok' : 'text-high'}`}>{passed}/{a.false_positive_tests.length}</div></div>
      </div>

      <div className="grid lg:grid-cols-2 gap-4">
        <section className="bg-panel border border-line rounded-lg p-4">
          <h2 className="text-sm font-medium text-white">Feature contributions</h2>
          <p className="text-xs text-mute">Share of the anomaly score each input explains, averaged over evaluated devices</p>
          <div className="h-60 mt-3">{chart.length === 0 ? <div className="h-full grid place-items-center text-xs text-mute">Run the simulation to see contributions.</div> : (
            <ResponsiveContainer><BarChart data={chart} layout="vertical" margin={{ left: 30 }}>
              <CartesianGrid stroke="#1f3158" strokeDasharray="3 3" horizontal={false} />
              <XAxis type="number" unit="%" stroke="#8a9bbf" fontSize={11} /><YAxis type="category" dataKey="name" width={130} stroke="#8a9bbf" fontSize={11} />
              <Tooltip contentStyle={{ background: '#12203f', border: '1px solid #1f3158', fontSize: 12 }} cursor={{ fill: '#ffffff08' }} />
              <Bar dataKey="contribution_pct" fill="#4aa8ff" radius={[0, 4, 4, 0]} /></BarChart></ResponsiveContainer>)}</div>
        </section>

        <section className="bg-panel border border-line rounded-lg p-4 space-y-3">
          <h2 className="text-sm font-medium text-white">Risk score breakdown</h2>
          {!cur ? <p className="text-xs text-mute">No evaluated devices yet.</p> : (<>
            <div className="flex flex-wrap gap-2">{devs.map(([k]) => (
              <button key={k} onClick={() => setSel(k)} className={`px-2.5 py-1 rounded text-xs font-mono border focus:outline-none focus-visible:ring-2 focus-visible:ring-signal ${cur[0] === k ? 'border-signal text-white bg-raised' : 'border-line text-mute'}`}>{k}</button>))}</div>
            <div className="flex items-center justify-between"><span className="text-3xl font-semibold text-white">{Math.round(cur[1].risk_score)}</span><RiskBadge level={cur[1].risk_level} /></div>
            <BreakdownBar breakdown={cur[1].breakdown} />
            <p className="text-xs text-mute font-mono">R = 0.25·S + 0.20·I + 0.20·C + 0.15·T + 0.20·M{cur[1].breakdown.raw_total !== cur[1].breakdown.total ? ` = ${cur[1].breakdown.raw_total}, capped to ${cur[1].breakdown.total}` : ` = ${cur[1].breakdown.total}`}</p>
          </>)}
        </section>
      </div>

      <section className="bg-panel border border-line rounded-lg p-4">
        <h2 className="text-sm font-medium text-white">False-positive testing</h2>
        <p className="text-xs text-mute mb-3">Labelled cases run through the live detection engine. Ordinary presence must not be flagged.</p>
        <div className="overflow-x-auto"><table className="w-full text-sm">
          <thead className="text-xs text-mute text-left"><tr>{['Case', 'Expected', 'Result', 'Score', ''].map(h => <th key={h} className="py-2 pr-4 font-normal">{h}</th>)}</tr></thead>
          <tbody>{a.false_positive_tests.map(t => (
            <tr key={t.case} className="border-t border-line"><td className="py-2 pr-4"><div className="text-slate-200">{t.case}</div><div className="text-xs text-mute">{t.why}</div></td>
              <td className="pr-4 text-xs text-mute">{t.expected.join(', ').replaceAll('_', ' ').toLowerCase()}</td>
              <td className="pr-4"><RiskBadge level={t.actual} /></td><td className="pr-4 font-mono">{t.risk_score}</td>
              <td><Badge kind={t.passed ? 'ACTIVE' : 'FAILED'}>{t.passed ? 'pass' : 'fail'}</Badge></td></tr>))}</tbody>
        </table></div>
      </section>
    </div>
  )
}
