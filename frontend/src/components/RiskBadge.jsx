import { RISK } from '../services/api'

export default function RiskBadge({ level, score }) {
  const r = RISK[level] || RISK.NORMAL
  return (
    <span className={`inline-flex items-center gap-2 text-xs font-medium ${r.color}`}>
      <span className={`h-2 w-2 rounded-full ${r.bg}`} />
      {r.label}{score != null && <span className="font-mono text-slate-300">{Math.round(score)}</span>}
    </span>
  )
}
