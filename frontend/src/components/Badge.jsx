const STYLES = {
  REAL: 'text-ok border-ok/50', SIMULATED: 'text-review border-review/50',
  FUTURE_HARDWARE: 'text-mute border-line', FUTURE_DATA: 'text-mute border-line',
  ONLINE: 'text-ok border-ok/50', OFFLINE: 'text-high border-high/50', ACTIVE: 'text-ok border-ok/50',
  STANDBY: 'text-slate-300 border-line', WAITING_FOR_DATA: 'text-mute border-line',
  QUEUED: 'text-signal border-signal/50', RETRYING: 'text-review border-review/50',
  TRANSMITTED: 'text-ok border-ok/50', DELIVERED_NETWORK: 'text-ok border-ok/50', FAILED: 'text-high border-high/50',
}
export default function Badge({ kind, children }) {
  return <span className={`inline-block text-xs border rounded-full px-2.5 py-0.5 whitespace-nowrap ${STYLES[kind] || 'text-slate-300 border-line'}`}>{children ?? kind.replaceAll('_', ' ').toLowerCase()}</span>
}
