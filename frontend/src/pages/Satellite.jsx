import { useCallback } from 'react'
import { api } from '../services/api'
import useApi from '../hooks/useApi'
import Badge from '../components/Badge'
import { fmtTime } from '../services/format'

const Card = ({ title, children }) => (
  <section className="bg-panel border border-line rounded-lg p-4 space-y-2"><h2 className="text-sm font-medium text-white">{title}</h2>{children}</section>
)

export default function Satellite({ refreshKey }) {
  const { data: c, error, setData } = useApi(useCallback(() => api.connectivity(), []), refreshKey)
  if (error) return <div className="p-6 text-high text-sm">Could not load connectivity: {error}</div>
  if (!c) return <div className="p-6 text-mute text-sm">Loading…</div>
  const sf = c.satellite_fallback
  const offline = c.network.status === 'OFFLINE'

  return (
    <div className="p-6 space-y-6 max-w-6xl">
      <header>
        <h1 className="text-2xl font-semibold text-white">Satellite connectivity</h1>
        <p className="text-mute text-sm mt-1">How position and emergency messages travel, with each part marked as real, simulated or future.</p>
      </header>
      <div className="bg-review/10 border border-review/40 rounded-md px-4 py-2 text-sm text-review">
        The satellite link on this page is a simulation. No satellite, NavIC receiver or satellite messenger is connected.
      </div>

      <div className="grid md:grid-cols-3 gap-4">
        <Card title="GNSS positioning">
          <Badge kind={c.gnss.status} />
          <dl className="text-sm space-y-1 text-slate-300">
            <div><dt className="inline text-mute">Sources in use: </dt><dd className="inline font-mono">{Object.entries(c.gnss.sources_in_use).map(([k, v]) => `${k}×${v}`).join(', ') || 'none yet'}</dd></div>
            <div><dt className="inline text-mute">Average accuracy: </dt><dd className="inline">{c.gnss.avg_accuracy_m != null ? `±${c.gnss.avg_accuracy_m} m` : '–'}</dd></div>
            <div><dt className="inline text-mute">Constellations: </dt><dd className="inline">{c.gnss.constellations.join(' · ')}</dd></div>
          </dl>
        </Card>
        <Card title="Conventional network">
          <Badge kind={c.network.status} />
          <button onClick={() => api.setNetwork(offline ? 'ONLINE' : 'OFFLINE').then(setData)}
            className="mt-2 px-3 py-1.5 rounded-md text-xs border border-line hover:bg-raised focus:outline-none focus-visible:ring-2 focus-visible:ring-signal">
            {offline ? 'Restore network' : 'Simulate network outage'}
          </button>
          <p className="text-xs text-mute">While offline, new alerts queue a compact packet for the satellite fallback.</p>
        </Card>
        <Card title="Satellite fallback (simulated)">
          <div className="flex gap-2"><Badge kind={sf.state} /><Badge kind="SIMULATED" /></div>
          <p className="text-sm text-slate-300">Satellite in view: <b className={sf.link_visible ? 'text-ok' : 'text-review'}>{sf.link_visible ? 'yes' : 'no'}</b></p>
          <p className="text-xs text-mute">Pass windows repeat every {sf.pass_period_s} s; up to {sf.max_attempts} attempts with backoff; packets ≤ {sf.max_packet_bytes} bytes.</p>
        </Card>
      </div>

      <Card title="Emergency message queue">
        {sf.queue.length === 0 ? <p className="text-sm text-mute">Empty. Use “Simulate network outage”, then run the simulation: alerts will queue here.</p> : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-xs text-mute text-left"><tr>{['Packet', 'Alert', 'Payload', 'Bytes', 'Channel', 'Status', 'Tries', 'Note'].map(h => <th key={h} className="py-2 pr-4 font-normal">{h}</th>)}</tr></thead>
              <tbody>{sf.queue.map(p => (
                <tr key={p.packet_id} className="border-t border-line">
                  <td className="py-2 pr-4 font-mono">#{p.packet_id}</td><td className="pr-4">#{p.alert_id}</td>
                  <td className="pr-4 font-mono text-xs">{p.payload}</td><td className="pr-4">{p.size_bytes}</td>
                  <td className="pr-4 text-xs">{p.channel === 'NETWORK' ? 'Network' : 'Satellite (sim)'}</td>
                  <td className="pr-4"><Badge kind={p.status} /></td><td className="pr-4">{p.attempts}</td>
                  <td className="text-xs text-mute">{p.last_note} · {fmtTime(p.created_at)}</td>
                </tr>))}</tbody>
            </table>
          </div>)}
      </Card>

      <Card title="What is real, simulated, or future">
        <ul className="divide-y divide-line">
          {c.capabilities.map(x => (
            <li key={x.name} className="py-2.5 flex flex-wrap items-start gap-3">
              <Badge kind={x.status} /><div className="flex-1 min-w-60"><div className="text-sm text-slate-200">{x.name}</div><div className="text-xs text-mute">{x.detail}</div></div>
            </li>))}
        </ul>
      </Card>
    </div>
  )
}
