// Backend timestamps are naive UTC; display them in IST.
export const toDate = (ts) => new Date(/Z|[+-]\d\d:\d\d$/.test(ts) ? ts : ts + 'Z')
export const fmtTime = (ts) => toDate(ts).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', hour12: false,
  day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }) + ' IST'
export const fmtDuration = (min) => min == null ? '–' : min >= 60 ? `${Math.floor(min / 60)} h ${Math.round(min % 60)} min` : `${Math.round(min)} min`
export const fmtCoord = (lat, lon) => `${lat.toFixed(4)}°N, ${lon.toFixed(4)}°E`
