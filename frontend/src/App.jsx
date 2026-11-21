import { useState, useCallback, useEffect, useRef } from 'react'
import Sidebar from './components/Sidebar'
import StatusDot from './components/StatusDot'
import SimControls from './components/SimControls'
import useAlertStream from './hooks/useAlertStream'
import { api } from './services/api'
import Overview from './pages/Overview'
import Live from './pages/Live'
import Anomaly from './pages/Anomaly'
import Alerts from './pages/Alerts'
import Zones from './pages/Zones'
import Analytics from './pages/Analytics'
import Satellite from './pages/Satellite'
import Settings from './pages/Settings'

const PAGES = { overview: Overview, live: Live, anomaly: Anomaly, alerts: Alerts, zones: Zones,
  analytics: Analytics, satellite: Satellite, settings: Settings }

export default function App() {
  const [page, setPage] = useState('overview')
  const [tick, setTick] = useState(0)          // bumped on every WebSocket event -> pages reload
  const [focus, setFocus] = useState(null)     // alert chosen with "View on map"
  const [lastEvent, setLastEvent] = useState(null)
  const [sim, setSim] = useState(null)
  const trails = useRef({})                // device_id -> [[lat, lon], ...] built from live events
  const onEvent = useCallback(ev => {
    if (ev.type === 'device_update') {
      const t = trails.current[ev.data.device_id] ||= []
      t.push([ev.data.latitude, ev.data.longitude]); if (t.length > 80) t.shift()
    } else if (ev.type === 'reset') trails.current = {}
    else if (ev.type === 'simulation_status') setSim(ev.data)
    setLastEvent(ev); setTick(t => t + 1)
  }, [])
  const connected = useAlertStream(onEvent)
  useEffect(() => { api.simulationStatus().then(setSim).catch(() => {}) }, [])
  const Page = PAGES[page]
  const viewOnMap = (alert) => { setFocus(alert); setPage('live') }

  return (
    <div className="h-full flex">
      <Sidebar page={page} onNavigate={setPage} />
      <main className="flex-1 overflow-auto">
        <div className="flex flex-wrap items-center justify-between gap-3 px-6 h-14 border-b border-line bg-panel/60">
          <SimControls sim={sim} onChange={setSim} />
          <StatusDot ok={connected} label={connected ? 'Live alert stream connected' : 'Alert stream offline, retrying'} />
        </div>
        <Page refreshKey={tick} lastEvent={lastEvent} focus={focus} trails={trails.current} onViewMap={viewOnMap} />
      </main>
    </div>
  )
}
