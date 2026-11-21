import { useCallback, useEffect, useState } from 'react'
import { api } from '../services/api'
import useApi from '../hooks/useApi'

const FIELDS = [
  ['stationary_radius_m', 'Stationary radius', 'metres', 'How far a device may drift and still count as staying put.'],
  ['stationary_duration_min', 'Stationary duration', 'minutes', 'How long before a device is evaluated at all.'],
  ['review_threshold', 'Review threshold', 'score', 'Score at which an alert needs human review.'],
  ['high_threshold', 'High-priority threshold', 'score', 'Score at which an alert needs urgent human verification.'],
]

export default function Settings() {
  const { data, reload } = useApi(useCallback(() => api.settings(), []), 0)
  const [form, setForm] = useState(null)
  const [msg, setMsg] = useState(null)
  useEffect(() => { if (data) setForm(data) }, [data])
  if (!form) return <div className="p-6 text-mute text-sm">Loading…</div>
  const save = async (e) => {
    e.preventDefault(); setMsg(null)
    try { await api.saveSettings(Object.fromEntries(FIELDS.map(([k]) => [k, Number(form[k])]))); setMsg({ ok: true, text: 'Saved. New thresholds apply to the next location update.' }); reload() }
    catch (err) { setMsg({ ok: false, text: err.response?.data?.detail?.[0]?.msg || err.response?.data?.detail || err.message }) }
  }
  return (
    <div className="p-6 max-w-3xl space-y-6">
      <header><h1 className="text-2xl font-semibold text-white">Settings</h1>
        <p className="text-mute text-sm mt-1">Detection thresholds. These are demonstration values, not validated probabilities.</p></header>
      <form onSubmit={save} className="bg-panel border border-line rounded-lg p-5 space-y-4">
        {FIELDS.map(([k, label, unit, help]) => (
          <label key={k} className="grid sm:grid-cols-[220px_1fr] gap-2 items-center">
            <span className="text-sm text-slate-200">{label}<span className="block text-xs text-mute">{help}</span></span>
            <span className="flex items-center gap-2"><input type="number" step="any" value={form[k]} onChange={e => setForm({ ...form, [k]: e.target.value })}
              className="w-32 bg-ink border border-line rounded-md px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-signal" /><span className="text-xs text-mute">{unit}</span></span>
          </label>))}
        <div className="flex items-center gap-4"><button className="px-4 py-2 rounded-md bg-signal text-ink text-sm font-medium focus:outline-none focus-visible:ring-2 focus-visible:ring-white">Save settings</button>
          {msg && <span className={`text-sm ${msg.ok ? 'text-ok' : 'text-high'}`}>{msg.text}</span>}</div>
      </form>
      <section className="bg-panel border border-line rounded-lg p-5 text-sm text-slate-300 space-y-2">
        <h2 className="text-white font-medium">Safeguards built in</h2>
        <ul className="list-disc pl-5 space-y-1 marker:text-mute">
          <li>Only consenting devices with pseudonymous IDs are processed. No names or phone numbers are stored.</li>
          <li>Stationary time, night-time or incident history alone can never raise a high-priority alert.</li>
          <li>Every alert needs a person to acknowledge, review, dismiss or resolve it. Nothing is dispatched automatically.</li>
        </ul>
      </section>
    </div>
  )
}
