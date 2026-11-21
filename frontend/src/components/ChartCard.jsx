export default function ChartCard({ title, subtitle, children, empty }) {
  return (
    <section className="bg-panel border border-line rounded-lg p-4">
      <h2 className="text-sm font-medium text-white">{title}</h2>
      {subtitle && <p className="text-xs text-mute mt-0.5">{subtitle}</p>}
      <div className="h-56 mt-3">
        {empty ? <div className="h-full grid place-items-center text-xs text-mute text-center px-6">{empty}</div> : children}
      </div>
    </section>
  )
}
