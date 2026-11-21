import { useCallback } from 'react'
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api } from '../services/api'
import useApi from '../hooks/useApi'
import StatCard from '../components/StatCard'
import ChartCard from '../components/ChartCard'

const COLORS = { NORMAL: '#2fc58a', REVIEW_REQUIRED: '#f5a524', HIGH_PRIORITY_VERIFICATION: '#f0455a' }
const LABEL = { NORMAL: 'Normal', REVIEW_REQUIRED: 'Review required', HIGH_PRIORITY_VERIFICATION: 'High priority' }
const GEO_COLOR = { 'Isolated + incident context': '#f0455a', Isolated: '#f5a524', 'Incident context': '#4aa8ff', 'Populated / other': '#2fc58a' }
const tip = { contentStyle: { background: '#12203f', border: '1px solid #1f3158', borderRadius: 6, fontSize: 12 }, cursor: { fill: '#ffffff08' } }
const axis = { stroke: '#8a9bbf', fontSize: 11, tickLine: false, axisLine: { stroke: '#1f3158' } }
const NO_ALERTS = 'No alerts yet. Alerts appear when a device stays put and the surrounding context is unusual.'

export default function Overview({ refreshKey }) {
  const { data: s, error } = useApi(useCallback(() => api.statistics(), []), refreshKey)
  const risk = Object.entries(s?.risk_distribution || {}).map(([k, v]) => ({ name: LABEL[k] || k, key: k, count: v }))
  const geo = Object.entries(s?.geo_distribution || {}).map(([k, v]) => ({ name: k, count: v }))
  const an = s?.anomaly_stats

  return (
    <div className="p-6 space-y-6">
      <header>
        <h1 className="text-2xl font-semibold text-white">Overview</h1>
        <p className="text-mute text-sm mt-1">Unusual stationary patterns across participating, consenting devices.</p>
      </header>
      {error && <div className="text-high text-sm">Backend unreachable: {error}. Start it with <code className="font-mono">uvicorn main:app --reload --port 8000</code>.</div>}

      <div className="grid grid-cols-2 xl:grid-cols-5 gap-4">
        <StatCard label="Participating devices" value={s?.participating_devices} />
        <StatCard label="Unusual stationary patterns" value={s?.unusual_stationary_patterns} tone="text-review" />
        <StatCard label="Awaiting verification" value={s?.pending_alerts} tone="text-review" />
        <StatCard label="High-priority review" value={s?.high_priority_alerts} tone="text-high" />
        <StatCard label="Resolved" value={s?.resolved_alerts} tone="text-ok" />
      </div>

      <div className="grid lg:grid-cols-2 gap-4">
        <ChartCard title="Alerts over time" subtitle="Alerts raised per minute of detection time" empty={!s?.alert_trend?.length && NO_ALERTS}>
          <ResponsiveContainer>
            <AreaChart data={s?.alert_trend}>
              <defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#4aa8ff" stopOpacity={0.5} /><stop offset="100%" stopColor="#4aa8ff" stopOpacity={0} /></linearGradient></defs>
              <CartesianGrid stroke="#1f3158" strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="time" {...axis} /><YAxis allowDecimals={false} {...axis} />
              <Tooltip {...tip} /><Area type="monotone" dataKey="alerts" stroke="#4aa8ff" fill="url(#g)" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Risk distribution" subtitle="Alerts by verification priority" empty={!risk.length && NO_ALERTS}>
          <ResponsiveContainer>
            <BarChart data={risk}>
              <CartesianGrid stroke="#1f3158" strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="name" {...axis} /><YAxis allowDecimals={false} {...axis} /><Tooltip {...tip} />
              <Bar dataKey="count" radius={[4, 4, 0, 0]}>{risk.map(r => <Cell key={r.key} fill={COLORS[r.key] || '#4aa8ff'} />)}</Bar>
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Geographical risk distribution" subtitle="What kind of place raised each alert" empty={!geo.length && NO_ALERTS}>
          <ResponsiveContainer>
            <BarChart data={geo} layout="vertical" margin={{ left: 40 }}>
              <CartesianGrid stroke="#1f3158" strokeDasharray="3 3" horizontal={false} />
              <XAxis type="number" allowDecimals={false} {...axis} /><YAxis type="category" dataKey="name" width={150} {...axis} /><Tooltip {...tip} />
              <Bar dataKey="count" radius={[0, 4, 4, 0]}>{geo.map(g => <Cell key={g.name} fill={GEO_COLOR[g.name] || '#4aa8ff'} />)}</Bar>
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <section className="bg-panel border border-line rounded-lg p-4">
          <h2 className="text-sm font-medium text-white">Anomaly detection statistics</h2>
          <p className="text-xs text-mute mt-0.5">Isolation Forest, trained on synthetic baseline behaviour</p>
          <dl className="grid grid-cols-2 gap-4 mt-5">
            {[['Devices tracked', an?.devices_tracked], ['Evaluated (stationary long enough)', an?.devices_evaluated],
              ['Flagged for review', an?.devices_flagged], ['Mean anomaly score', an?.mean_anomaly_score]].map(([k, v]) => (
              <div key={k}><dt className="text-xs text-mute">{k}</dt><dd className="text-2xl font-semibold text-white mt-1">{v ?? '–'}</dd></div>
            ))}
          </dl>
        </section>
      </div>
    </div>
  )
}
