import { useCallback, useMemo } from 'react'
import { MapContainer, TileLayer, GeoJSON } from 'react-leaflet'
import { api } from '../services/api'
import useApi from '../hooks/useApi'
import { ZONE_STYLE, ZONE_LABEL } from '../components/zoneStyle'

export default function Zones() {
  const { data: z } = useApi(useCallback(() => api.zones(), []), 0)
  const feats = z?.features || []
  const rows = useMemo(() => feats.filter(f => f.properties.zone_type !== 'road').map(f => f.properties), [feats])
  return (
    <div className="flex flex-col lg:flex-row h-[calc(100vh-3.5rem)]">
      <div className="flex-1 min-h-[400px]">
        <MapContainer center={[23.17, 77.39]} zoom={11} className="h-full w-full">
          <TileLayer attribution='&copy; OpenStreetMap contributors' url="https://tile.openstreetmap.org/{z}/{x}/{y}.png" />
          {feats.length > 0 && <GeoJSON key={feats.length} data={z} style={f => ZONE_STYLE[f.properties.zone_type]}
            onEachFeature={(f, l) => l.bindTooltip(`${f.properties.name}${f.properties.context_score ? ` · context ${f.properties.context_score}` : ''}`, { sticky: true })} />}
        </MapContainer>
      </div>
      <aside className="lg:w-96 shrink-0 border-l border-line bg-panel overflow-auto p-4 space-y-4">
        <div><h1 className="text-lg font-semibold text-white">Geographical risk zones</h1>
          <p className="text-xs text-mute mt-1">Zones supply context to the score. A zone never raises an alert on its own.</p></div>
        {Object.entries(ZONE_LABEL).filter(([t]) => t !== 'road').map(([t, label]) => (
          <section key={t}><h2 className="text-sm text-slate-200 flex items-center gap-2"><span className="h-2.5 w-4 rounded-sm" style={{ background: ZONE_STYLE[t].color }} />{label}</h2>
            <ul className="mt-1.5 space-y-1">{rows.filter(r => r.zone_type === t).map(r => (
              <li key={r.zone_id} className="flex justify-between text-xs text-mute"><span>{r.name}</span><span className="font-mono text-slate-300">{r.context_score}</span></li>))}</ul></section>))}
        <p className="text-xs text-mute border-t border-line pt-3">All zones are simulated demonstration data. Replace data/geographical_zones.geojson with real land-cover, settlement and road extracts to deploy.</p>
      </aside>
    </div>
  )
}
