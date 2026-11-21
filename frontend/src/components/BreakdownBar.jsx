const PARTS = [
  ['S', 'Stationary', 'bg-signal'], ['I', 'Isolation', 'bg-review'], ['C', 'Incident context', 'bg-high'],
  ['T', 'Time of day', 'bg-violet-400'], ['M', 'Anomaly (ML)', 'bg-ok'],
]

/** Stacked bar of weighted points per factor: shows exactly how the score was built. */
export default function BreakdownBar({ breakdown }) {
  if (!breakdown?.contributions) return null
  const c = breakdown.contributions
  return (
    <div>
      <div className="flex h-2 rounded overflow-hidden bg-line">
        {PARTS.map(([k, , cls]) => <div key={k} className={cls} style={{ width: `${c[k]}%` }} title={`${k}: ${c[k]} pts`} />)}
      </div>
      <div className="flex flex-wrap gap-x-4 gap-y-1 mt-2 text-xs text-mute">
        {PARTS.map(([k, name, cls]) => (
          <span key={k} className="inline-flex items-center gap-1.5">
            <span className={`h-2 w-2 rounded-sm ${cls}`} />{name} <span className="font-mono text-slate-300">{c[k]}</span>
            <span className="text-mute/70">({Math.round(breakdown[k])})</span>
          </span>
        ))}
      </div>
      {breakdown.caps_applied?.length > 0 && (
        <p className="text-xs text-review mt-2">{breakdown.caps_applied[0]}</p>
      )}
    </div>
  )
}
