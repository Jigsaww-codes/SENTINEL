export default function Placeholder({ title, phase }) {
  return (
    <div className="p-6">
      <h1 className="text-2xl font-semibold text-white">{title}</h1>
      <div className="mt-6 bg-panel border border-dashed border-line rounded-lg p-8 text-mute text-sm">
        Scheduled for Phase {phase}.
      </div>
    </div>
  )
}
