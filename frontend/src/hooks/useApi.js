import { useCallback, useEffect, useState } from 'react'

/** Loads data from `fn`, reloading whenever `refreshKey` changes (bumped by WebSocket events). */
export default function useApi(fn, refreshKey = 0, initial = null) {
  const [data, setData] = useState(initial)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)
  const run = useCallback(() => fn().then(d => { setData(d); setError(null) })
    .catch(e => setError(e.message)).finally(() => setLoading(false)), [fn])
  useEffect(() => { run() }, [run, refreshKey])
  return { data, error, loading, reload: run, setData }
}
