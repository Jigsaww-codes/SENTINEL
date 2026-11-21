export default function StatusDot({ ok, label }) {
  return (
    <span className="inline-flex items-center gap-2 text-xs text-mute">
      <span className={`h-2 w-2 rounded-full ${ok ? 'bg-ok' : 'bg-high'}`} />
      {label}
    </span>
  )
}
