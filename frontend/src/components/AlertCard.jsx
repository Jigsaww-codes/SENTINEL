import { useState } from 'react'
import { MapPin, Check, Eye, X, CheckCheck, Clock } from 'lucide-react'
import RiskBadge from './RiskBadge'
import BreakdownBar from './BreakdownBar'
import { fmtTime, fmtDuration, fmtCoord } from '../services/format'

const STATUS_STYLE = {
  NEW: 'text-signal border-signal/50', ACKNOWLEDGED: 'text-slate-300 border-line',
  UNDER_REVIEW: 'text-review border-review/50', DISMISSED: 'text-mute border-line', RESOLVED: 'text-ok border-ok/50',
}
const STATUS_LABEL = { NEW: 'New', ACKNOWLEDGED: 'Acknowledged', UNDER_REVIEW: 'Under review',
  DISMISSED: 'Dismissed as false positive', RESOLVED: 'Resolved' }

export default function AlertCard({ alert: a, onViewMap, onUpdate, selected }) {
  const [note, setNote] = useState(a.response_note || '')
  const [welfare, setWelfare] = useState(a.welfare_check_considered ?? false)
  const [busy, setBusy] = useState(false)
  const closed = a.status === 'DISMISSED' || a.status === 'RESOLVED'
  const border = a.risk_level === 'HIGH_PRIORITY_VERIFICATION' ? 'border-l-high' : 'border-l-review'

  const act = async (status) => {
    setBusy(true)
    try { await onUpdate(a.alert_id, { status, note: note || null, welfare_check_considered: welfare }) }
    finally { setBusy(false) }
  }
  const Btn = ({ status, icon: Icon, children, disabled }) => (
    <button disabled={busy || disabled || a.status === status} onClick={() => act(status)}
      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs border border-line text-slate-200
        hover:bg-raised disabled:opacity-40 disabled:hover:bg-transparent focus:outline-none focus-visible:ring-2 focus-visible:ring-signal">
      <Icon size={14} />{children}
    </button>
  )

  return (
    <article className={`bg-panel border border-line border-l-4 ${border} rounded-lg p-4 space-y-3 ${selected ? 'ring-1 ring-signal' : ''}`}>
      <header className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <div className="flex items-center gap-3">
            <h3 className="font-semibold text-white">Alert #{a.alert_id}</h3>
            <RiskBadge level={a.risk_level} score={a.risk_score} />
          </div>
          <div className="text-xs text-mute mt-1 font-mono">{a.device_id} · {fmtCoord(a.latitude, a.longitude)}</div>
        </div>
        <span className={`text-xs border rounded-full px-2.5 py-0.5 ${STATUS_STYLE[a.status]}`}>{STATUS_LABEL[a.status]}</span>
      </header>

      <div className="flex gap-6 text-sm">
        <span className="inline-flex items-center gap-1.5 text-slate-300"><Clock size={14} className="text-mute" />Stationary {fmtDuration(a.stationary_minutes)}</span>
        <span className="text-mute">Detected {fmtTime(a.created_at)}</span>
      </div>

      <ul className="text-sm text-slate-300 space-y-1 list-disc pl-5 marker:text-mute">
        {a.reasons.map((r, i) => <li key={i}>{r}</li>)}
      </ul>
      <BreakdownBar breakdown={a.breakdown} />

      <div className="grid sm:grid-cols-[1fr_auto] gap-3 items-end pt-1">
        <div className="space-y-2">
          <textarea value={note} onChange={e => setNote(e.target.value)} rows={2} maxLength={500} disabled={busy}
            placeholder="Reviewer note (e.g. contacted device owner, patrol informed)"
            className="w-full bg-ink border border-line rounded-md px-3 py-2 text-sm placeholder:text-mute/70 focus:outline-none focus:ring-2 focus:ring-signal" />
          <label className="inline-flex items-center gap-2 text-xs text-mute cursor-pointer">
            <input type="checkbox" checked={welfare} onChange={e => setWelfare(e.target.checked)} className="accent-signal" />
            A welfare check or patrol was considered
          </label>
        </div>
      </div>

      <footer className="flex flex-wrap gap-2">
        <button onClick={() => onViewMap?.(a)}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs bg-signal/15 text-signal border border-signal/40 hover:bg-signal/25 focus:outline-none focus-visible:ring-2 focus-visible:ring-signal">
          <MapPin size={14} />View on map
        </button>
        <Btn status="ACKNOWLEDGED" icon={Check} disabled={a.status !== 'NEW'}>Acknowledge</Btn>
        <Btn status="UNDER_REVIEW" icon={Eye} disabled={closed}>Review</Btn>
        <Btn status="DISMISSED" icon={X} disabled={closed}>Dismiss</Btn>
        <Btn status="RESOLVED" icon={CheckCheck} disabled={closed}>Resolve</Btn>
      </footer>
    </article>
  )
}
