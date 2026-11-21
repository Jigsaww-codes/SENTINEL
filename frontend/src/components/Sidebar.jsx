import { LayoutDashboard, Radar, BrainCircuit, Siren, Layers, LineChart, Satellite, Settings, Shield } from 'lucide-react'

export const NAV = [
  { id: 'overview', label: 'Overview', icon: LayoutDashboard },
  { id: 'live', label: 'Live Location Monitoring', icon: Radar },
  { id: 'anomaly', label: 'Anomaly Detection', icon: BrainCircuit },
  { id: 'alerts', label: 'Emergency Alerts', icon: Siren },
  { id: 'zones', label: 'Geographical Risk Zones', icon: Layers },
  { id: 'analytics', label: 'AI Analytics', icon: LineChart },
  { id: 'satellite', label: 'Satellite Connectivity', icon: Satellite },
  { id: 'settings', label: 'Settings', icon: Settings },
]

export default function Sidebar({ page, onNavigate, badges = {} }) {
  return (
    <aside className="w-64 shrink-0 bg-panel border-r border-line flex flex-col">
      <div className="px-5 py-5 border-b border-line flex items-center gap-3">
        <Shield className="text-signal" size={26} />
        <div>
          <div className="font-semibold tracking-wide text-white">SENTINEL</div>
          <div className="text-xs text-mute">Public safety command centre</div>
        </div>
      </div>
      <nav className="flex-1 p-3 space-y-1">
        {NAV.map(({ id, label, icon: Icon }) => {
          const active = page === id
          return (
            <button key={id} onClick={() => onNavigate(id)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-md text-sm text-left transition-colors
                focus:outline-none focus-visible:ring-2 focus-visible:ring-signal
                ${active ? 'bg-raised text-white border-l-2 border-signal' : 'text-mute hover:bg-raised/60 hover:text-slate-200 border-l-2 border-transparent'}`}>
              <Icon size={18} />
              <span className="flex-1">{label}</span>
              {badges[id] > 0 && <span className="text-xs bg-high text-white rounded-full px-2 py-0.5">{badges[id]}</span>}
            </button>
          )
        })}
      </nav>
      <div className="p-4 text-xs text-mute border-t border-line leading-relaxed">
        Decision support only. Every alert needs human verification before any response.
      </div>
    </aside>
  )
}
