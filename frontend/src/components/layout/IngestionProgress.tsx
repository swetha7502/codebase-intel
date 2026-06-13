import { useIngestionProgress } from '../../hooks/useIngestionProgress'
import { Loader2, CheckCircle, XCircle } from 'lucide-react'

interface Props { repoId: string; onComplete: () => void }

const STAGE_LABELS: Record<string, string> = {
  cloning: 'Cloning repository',
  parsing: 'Parsing source files',
  embedding: 'Embedding symbols',
  complete: 'Indexing complete',
  failed: 'Ingestion failed',
}

export function IngestionProgress({ repoId, onComplete }: Props) {
  const progress = useIngestionProgress(repoId, true)

  if (!progress) {
    return (
      <div className="card p-6 flex items-center gap-3">
        <Loader2 size={18} className="animate-spin text-brand-400" />
        <p className="text-sm text-slate-400">Initializing ingestion pipeline…</p>
      </div>
    )
  }

  if (progress.stage === 'complete') {
    setTimeout(onComplete, 1500)
  }

  const isError = progress.stage === 'failed'

  return (
    <div className="card p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {isError
            ? <XCircle size={16} className="text-red-400" />
            : progress.stage === 'complete'
            ? <CheckCircle size={16} className="text-emerald-400" />
            : <Loader2 size={16} className="animate-spin text-brand-400" />
          }
          <span className="text-sm font-medium text-slate-200">
            {STAGE_LABELS[progress.stage] ?? progress.stage}
          </span>
        </div>
        <span className="text-xs text-slate-500 font-mono">{progress.percent}%</span>
      </div>

      <div className="w-full bg-surface-800 rounded-full h-1.5">
        <div
          className={`h-1.5 rounded-full transition-all duration-500 ${isError ? 'bg-red-500' : 'bg-brand-500'}`}
          style={{ width: `${progress.percent}%` }}
        />
      </div>

      <p className="text-xs text-slate-500">{progress.message}</p>
    </div>
  )
}
