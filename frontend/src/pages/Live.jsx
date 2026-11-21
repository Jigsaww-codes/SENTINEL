import { useCallback, useEffect, useMemo } from 'react'
import { MapContainer, TileLayer, GeoJSON, CircleMarker, Polyline, Marker, Popup, LayersControl, useMap } from 'react-leaflet'
import L from 'leaflet'
import { api } from '../services/api'
import useApi from '../hooks/useApi'
import RiskBadge from '../components/RiskBadge'
import { fmtDuration } from '../services/format'
import { ZONE_STYLE, ZONE_LABEL } from '../components/zoneStyle'

const CENTER = [23.17, 77.39]
const LEVEL_COLOR = { NORMAL: '#2fc58a', REVIEW_REQUIRED: '#f5a524', HIGH_PRIORITY_VERIFICATION: '#f0455a' }
const ringIcon = (c) => L.divIcon({ className: '', iconSize: [44, 44], iconAnchor: [22, 22],
  html: `<span class="sentinel-ring" style="--c:${c}"></span>` })

function FlyTo({ target }) {
  const map = useMap()
  useEffect(() => { if (target) map.flyTo([target.latitude, target.longitude], 14, { duration: 1.2 }) }, [target, map])
  return null
}

export default function Live({ refreshKey, focus, trails = {}, onViewMap }) {
  const { data: devices } = useApi(useCallback(() => api.devices(), []), refreshKey, [])
  const { data: zones } = useApi(useCallback(() => api.zones(), []), 0)
  const { data: alerts } = useApi(useCallback(() => api.alerts(), []), refreshKey, [])
  const open = alerts.filter(a => !['DISMISSED', 'RESOLVED'].includes(a.status))
  const byType = useMemo(() => Object.fromEntries(Object.keys(ZONE_STYLE).map(t =>
    [t, { type: 'FeatureCollection', features: (zones?.features || []).filter(f => f.properties.zone_type === t) }])), [zones])
  const flyTarget = focus || null

  return (
    <div className="flex flex-col lg:flex-row h-[calc(100vh-3.5rem)]">
      <div className="flex-1 min-h-[420px] relative">
        <MapContainer center={CENTER} zoom={11} className="h-full w-full" zoomControl>
          <TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://tile.openstreetmap.org/{z}/{x}/{y}.png" />
          <FlyTo target={flyTarget} />
          <LayersControl position="topright">
            {Object.entries(byType).map(([t, fc]) => fc.features.length > 0 && (
              <LayersControl.Overlay key={t + fc.features.length} checked name={ZONE_LABEL[t]}>
                <GeoJSON data={fc} style={() => ZONE_STYLE[t]}
                  onEachFeature={(f, l) => l.bindTooltip(`${f.properties.name} (simulated)`, { sticky: true })} />
              </LayersControl.Overlay>
            ))}
          </LayersControl>

          {Object.entries(trails).map(([id, pts]) => pts.length > 1 &&
            <Polyline key={id} positions={pts} pathOptions={{ color: '#8a9bbf', weight: 2, opacity: 0.6, dashArray: '2 6' }} />)}

          {open.map(a => (
            <Marker key={'ring' + a.alert_id} position={[a.latitude, a.longitude]} interactive={false}
              icon={ringIcon(LEVEL_COLOR[a.risk_level])} />
          ))}
          {devices.map(d => (
            <CircleMarker key={d.device_id} center={[d.latitude, d.longitude]} radius={9}
              pathOptions={{ color: '#070d1c', weight: 2, fillColor: LEVEL_COLOR[d.risk_level], fillOpacity: 1 }}>
              <Popup minWidth={260}>
                <div className="text-slate-900 text-xs space-y-1.5">
                  <div className="font-semibold text-sm">{d.device_id}</div>
                  <div className="font-mono">{d.latitude.toFixed(5)}, {d.longitude.toFixed(5)}</div>
                  <div>Stationary: <b>{fmtDuration(d.stationary_minutes)}</b> · Risk <b>{Math.round(d.risk_score)}</b></div>
                  <div>Source: {d.source}{d.accuracy ? ` · ±${d.accuracy} m` : ''}</div>
                  {d.reasons?.length > 0 && <ul className="list-disc pl-4 text-slate-700">{d.reasons.map((r, i) => <li key={i}>{r}</li>)}</ul>}
                </div>
              </Popup>
            </CircleMarker>
          ))}
        </MapContainer>
        {devices.length === 0 && (
          <div className="absolute z-[500] left-1/2 top-6 -translate-x-1/2 bg-panel/95 border border-line rounded-md px-4 py-2 text-xs text-slate-300">
            No devices yet. Press Start simulation above to see participating devices appear.
          </div>
        )}
      </div>

      <aside className="lg:w-80 shrink-0 border-t lg:border-t-0 lg:border-l border-line bg-panel overflow-auto p-4 space-y-3">
        <h2 className="text-sm font-medium text-white">Participating devices</h2>
        {devices.map(d => {
          const al = open.find(a => a.device_id === d.device_id)
          return (
            <button key={d.device_id} onClick={() => onViewMap?.(al || d)}
              className="w-full text-left bg-ink border border-line rounded-md p-3 hover:border-signal/60 focus:outline-none focus-visible:ring-2 focus-visible:ring-signal">
              <div className="flex justify-between items-center"><span className="font-mono text-sm text-white">{d.device_id}</span>
                <RiskBadge level={d.risk_level} score={d.risk_score || null} /></div>
              <div className="text-xs text-mute mt-1">{d.stationary_minutes > 0 ? `Stationary ${fmtDuration(d.stationary_minutes)}` : 'Moving'} · {d.source}</div>
            </button>
          )
        })}
        <div className="pt-2 text-xs text-mute space-y-1">
          <div className="text-slate-300 font-medium mb-1">Map key</div>
          {Object.entries(ZONE_LABEL).map(([t, l]) => (
            <div key={t} className="flex items-center gap-2"><span className="h-2.5 w-4 rounded-sm" style={{ background: ZONE_STYLE[t].color, opacity: .8 }} />{l}</div>
          ))}
          <p className="pt-2">Zones and roads are simulated demonstration data, not real incidents or surveyed boundaries.</p>
        </div>
      </aside>
    </div>
  )
}
