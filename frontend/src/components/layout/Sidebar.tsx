import { useState } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { Code2, Search, GitBranch, MessageSquare, Plus, Trash2, RefreshCw, AlertCircle, CheckCircle, Loader2 } from 'lucide-react'
import { reposApi, Repo } from "../../lib/api";

interface SidebarProps {
  repos: Repo[]
  onRepoAdded: () => void
  onRepoDeleted: (id: string) => void
}

const STATUS_ICON = {
  complete: <CheckCircle size={12} className="text-emerald-400" />,
  failed: <AlertCircle size={12} className="text-red-400" />,
  pending: <Loader2 size={12} className="text-slate-400 animate-spin" />,
  cloning: <Loader2 size={12} className="text-blue-400 animate-spin" />,
  parsing: <Loader2 size={12} className="text-amber-400 animate-spin" />,
  embedding: <Loader2 size={12} className="text-brand-400 animate-spin" />,
}

export function Sidebar({ repos, onRepoAdded, onRepoDeleted }: SidebarProps) {
  const [adding, setAdding] = useState(false)
  const [url, setUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const navigate = useNavigate()

  async function handleAdd() {
    if (!url.trim()) return
    setLoading(true)
    setError('')
    try {
      const res = await reposApi.add(url.trim())
      setUrl('')
      setAdding(false)
      onRepoAdded()
      navigate(`/repo/${res.data.id}`)
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Failed to add repository')
    } finally {
      setLoading(false)
    }
  }

  async function handleDelete(e: React.MouseEvent, id: string) {
    e.preventDefault()
    e.stopPropagation()
    await reposApi.delete(id)
    onRepoDeleted(id)
  }

  return (
    <aside className="w-64 bg-surface-900 border-r border-slate-800 flex flex-col h-screen sticky top-0">
      {/* Logo */}
      <div className="px-5 py-4 border-b border-slate-800 flex items-center gap-2.5">
        <div className="w-7 h-7 bg-brand-600 rounded-lg flex items-center justify-center">
          <Code2 size={14} className="text-white" />
        </div>
        <span className="font-semibold text-sm text-slate-100">Codebase Intel</span>
      </div>

      {/* Repos list */}
      <div className="flex-1 overflow-y-auto py-3">
        <div className="px-3 mb-1 flex items-center justify-between">
          <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">Repositories</span>
          <button
            onClick={() => setAdding(true)}
            className="p-1 hover:bg-surface-800 rounded text-slate-500 hover:text-slate-300 transition-colors"
            title="Add repository"
          >
            <Plus size={13} />
          </button>
        </div>

        {adding && (
          <div className="mx-3 mb-2 p-2.5 bg-surface-850 border border-slate-700 rounded-lg">
            <input
              className="input text-xs mb-2"
              placeholder="https://github.com/owner/repo"
              value={url}
              onChange={e => setUrl(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleAdd()}
              autoFocus
            />
            {error && <p className="text-red-400 text-xs mb-2">{error}</p>}
            <div className="flex gap-1.5">
              <button className="btn-primary flex-1 py-1 text-xs" onClick={handleAdd} disabled={loading}>
                {loading ? 'Adding…' : 'Add'}
              </button>
              <button className="btn-ghost text-xs py-1" onClick={() => { setAdding(false); setError('') }}>
                Cancel
              </button>
            </div>
          </div>
        )}

        {repos.length === 0 && !adding && (
          <p className="text-xs text-slate-600 px-4 py-2">No repos yet. Click + to add one.</p>
        )}

        {repos.map(repo => (
          <NavLink
            key={repo.id}
            to={`/repo/${repo.id}`}
            className={({ isActive }) =>
              `flex items-center gap-2 mx-2 px-2.5 py-2 rounded-lg text-sm group transition-colors ${
                isActive ? 'bg-brand-900/50 text-slate-100' : 'text-slate-400 hover:bg-surface-800 hover:text-slate-200'
              }`
            }
          >
            <span className="flex-shrink-0">{STATUS_ICON[repo.status] ?? <Loader2 size={12} />}</span>
            <span className="truncate flex-1 font-mono text-xs">{repo.name}</span>
            <button
              onClick={e => handleDelete(e, repo.id)}
              className="opacity-0 group-hover:opacity-100 p-0.5 hover:text-red-400 transition-all"
              title="Delete"
            >
              <Trash2 size={11} />
            </button>
          </NavLink>
        ))}
      </div>

      {/* Nav links */}
      <div className="border-t border-slate-800 py-2 px-2">
        <NavLink to="/" end className={({ isActive }) =>
          `flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors ${isActive ? 'text-slate-100 bg-surface-800' : 'text-slate-500 hover:text-slate-300'}`
        }>
          <GitBranch size={14} />
          <span>Home</span>
        </NavLink>
      </div>
    </aside>
  )
}
