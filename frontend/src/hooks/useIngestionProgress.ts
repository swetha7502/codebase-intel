import { useState, useEffect, useRef } from 'react'

export interface ProgressEvent {
  stage: string
  message: string
  percent: number
}

export function useIngestionProgress(repoId: string | null, active: boolean) {
  const [progress, setProgress] = useState<ProgressEvent | null>(null)
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    if (!repoId || !active) return

    const ws = new WebSocket(`ws://localhost:8000/ws/ingestion/${repoId}`)
    wsRef.current = ws

    ws.onmessage = (e) => {
      const data: ProgressEvent = JSON.parse(e.data)
      setProgress(data)
    }

    ws.onerror = () => {
      setProgress({ stage: 'failed', message: 'Connection error', percent: 0 })
    }

    return () => ws.close()
  }, [repoId, active])

  return progress
}
