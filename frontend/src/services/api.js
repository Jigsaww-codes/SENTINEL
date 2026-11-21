// API client. Shapes mirror backend/schemas.py.
import axios from 'axios'

const http = axios.create({ baseURL: '/api', timeout: 10000 })

export const api = {
  health: () => http.get('/health').then(r => r.data),
  devices: () => http.get('/devices').then(r => r.data),
  alerts: (status) => http.get('/alerts', { params: status ? { status } : {} }).then(r => r.data),
  alert: (id) => http.get(`/alerts/${id}`).then(r => r.data),
  updateAlert: (id, body) => http.patch(`/alerts/${id}`, body).then(r => r.data),
  statistics: () => http.get('/statistics').then(r => r.data),
  zones: () => http.get('/zones').then(r => r.data),
  analytics: () => http.get('/analytics').then(r => r.data),
  connectivity: () => http.get('/connectivity').then(r => r.data),
  startSimulation: () => http.post('/simulation/start').then(r => r.data),
  stopSimulation: () => http.post('/simulation/stop').then(r => r.data),
  setNetwork: (status) => http.post('/connectivity/network', { status }).then(r => r.data),
  settings: () => http.get('/settings').then(r => r.data),
  saveSettings: (b) => http.put('/settings', b).then(r => r.data),
  resetDemo: () => http.post('/simulation/reset').then(r => r.data),
  simulationStatus: () => http.get('/simulation/status').then(r => r.data),
}

export const RISK = {
  NORMAL: { label: 'Normal', color: 'text-ok', bg: 'bg-ok' },
  REVIEW_REQUIRED: { label: 'Review required', color: 'text-review', bg: 'bg-review' },
  HIGH_PRIORITY_VERIFICATION: { label: 'High-priority verification', color: 'text-high', bg: 'bg-high' },
}
