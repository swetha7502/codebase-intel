import { useState, useEffect, useCallback } from 'react'
import { useParams } from 'react-router-dom'
import { GitBranch, Search, MessageSquare, RefreshCw, Star, FileCode, FunctionSquare, Boxes, AlertCircle, Loader2 } from 'lucide-react'
import { reposApi, Repo } from '../lib/api'
import { IngestionProgress } from '../components/layout/IngestionProgress'
import { DependencyGraphView } from '../components/graph/DependencyGraphView'
import { SearchPanel } from '../components/search/SearchPanel'
import { QAPanel } from '../components/search/QAPanel'

type Tab = 'graph' | 'search' | 'qa'

const IN_PROGRESS_STATUSES = ['pending', 'cloning', 'parsing', 'embedding']

export function RepoPage() {
  const { id } = useParams<{ id: string }>()
  const [repo, setRepo] = useState<Repo | null>(null)
  const [tab, setTab] = useState<Tab>('graph')
  const [loading, setLoading] = useState(true)

  const fetchRepo = useCallback(async () => {
    if (!id) return
    const res = await reposApi.get(id)
    setRepo(res.data)
    setLoading(false)
  }, [id])

  useEffect(() => { fetchRepo() }, [fetchRepo])

  // Poll for status if ingestion is in progress
  useEffect(() => {
    if (!repo || !IN_PROGRESS_STATUSES.includes(repo.status)) return
    const interval = setInterval(fetchRepo, 3000)
    return () => clearInterval(interval)
  }, [repo, fetchRepo])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 size={20} className="animate-spin text-brand-400" />
      </div>
    )
  }

  if (!repo) return <div className="p-8 text-slate-500">Repository not found</div>

  const isIndexing = IN_PROGRESS_STATUSES.includes(repo.status)
  const isFailed = repo.status === 'failed'

  return (
    <div className="p-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2 text-xs text-slate-500 mb-1">
              <span>{repo.owner}</span>
              <span>/</span>
            </div>
            <h1 className="text-2xl font-semibold text-slate-100 font-mono">{repo.name}</h1>
            {repo.description && (
              <p className="text-sm text-slate-500 mt-1">{repo.description}</p>
            )}
          </div>
          <a
            href={repo.github_url}
            target="_blank"
            rel="noopener noreferrer"
            className="btn-ghost flex items-center gap-1.5"
          >
            <GitBranch size={13} />
            GitHub ↗
          </a>
        </div>

        {/* Stats */}
        {repo.status === 'complete' && (
          <div className="flex items-center gap-5 mt-4 text-xs text-slate-500">
            {repo.language && (
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-blue-400" />
                {repo.language}
              </span>
            )}
            <span className="flex items-center gap-1.5"><Star size={11} /> {repo.star_count.toLocaleString()}</span>
            <span className="flex items-center gap-1.5"><FileCode size={11} /> {repo.file_count} files</span>
            <span className="flex items-center gap-1.5"><FunctionSquare size={11} /> {repo.function_count} functions</span>
            <span className="flex items-center gap-1.5"><Boxes size={11} /> {repo.class_count} classes</span>
          </div>
        )}
      </div>

      {/* Ingestion in progress */}
      {isIndexing && (
        <IngestionProgress repoId={repo.id} onComplete={fetchRepo} />
      )}

      {/* Error */}
      {isFailed && (
        <div className="card p-4 flex items-start gap-3 border-red-900/50 bg-red-950/20">
          <AlertCircle size={16} className="text-red-400 mt-0.5 flex-shrink-0" />
          <div>
            <p className="text-sm font-medium text-red-300">Ingestion failed</p>
            <p className="text-xs text-red-400 mt-0.5">{repo.error_message}</p>
            <button
              className="text-xs text-red-400 hover:text-red-300 mt-2 underline"
              onClick={() => { reposApi.reindex(repo.id); fetchRepo() }}
            >
              Retry indexing
            </button>
          </div>
        </div>
      )}

      {/* Content tabs */}
      {repo.status === 'complete' && (
        <>
          <div className="flex gap-1 border-b border-slate-800 mb-6">
            {([
              { id: 'graph', label: 'Dependency Graph', icon: <GitBranch size={13} /> },
              { id: 'search', label: 'Semantic Search', icon: <Search size={13} /> },
              { id: 'qa', label: 'Ask Codebase', icon: <MessageSquare size={13} /> },
            ] as const).map(t => (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className={`flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors -mb-px ${
                  tab === t.id
                    ? 'border-brand-500 text-slate-100'
                    : 'border-transparent text-slate-500 hover:text-slate-300'
                }`}
              >
                {t.icon}
                {t.label}
              </button>
            ))}
          </div>

          {tab === 'graph' && <DependencyGraphView repoId={repo.id} />}
          {tab === 'search' && <SearchPanel repoId={repo.id} />}
          {tab === 'qa' && <QAPanel repoId={repo.id} />}
        </>
      )}
    </div>
  )
}
