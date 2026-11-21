export default function StatCard({ label, value, tone = 'text-white', hint }) {
  return (
    <div className="bg-panel border border-line rounded-lg p-4">
      <div className="text-sm text-mute">{label}</div>
      <div className={`text-3xl font-semibold mt-1 ${tone}`}>{value ?? '–'}</div>
      {hint && <div className="text-xs text-mute mt-1">{hint}</div>}
    </div>
  )
}
