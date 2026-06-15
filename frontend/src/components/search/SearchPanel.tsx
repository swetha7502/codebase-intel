import { useState } from 'react'
import { Search, Code2, FunctionSquare, Boxes } from 'lucide-react'
import { reposApi, SearchResult } from '../../lib/api'
import MonacoEditor from '@monaco-editor/react'

interface Props { repoId: string }

const KIND_ICON: Record<string, React.ReactNode> = {
  function: <FunctionSquare size={12} className="text-brand-400" />,
  method: <FunctionSquare size={12} className="text-amber-400" />,
  class: <Boxes size={12} className="text-emerald-400" />,
}

// Maps file extensions to Monaco's built-in language IDs so the code
// viewer gets correct syntax highlighting for Python and JS/TS/TSX files.
const EXT_TO_MONACO_LANG: Record<string, string> = {
  py: 'python',
  js: 'javascript', jsx: 'javascript', mjs: 'javascript', cjs: 'javascript',
  ts: 'typescript', tsx: 'typescript',
}

function monacoLanguageFor(filePath: string): string {
  const fileName = filePath.split('/').pop() ?? ''
  const ext = fileName.includes('.') ? fileName.split('.').pop()?.toLowerCase() : undefined
  return (ext && EXT_TO_MONACO_LANG[ext]) || 'plaintext'
}

export function SearchPanel({ repoId }: Props) {
  const [query, setQuery] = useState('')
  const [kind, setKind] = useState('')
  const [results, setResults] = useState<SearchResult[]>([])
  const [loading, setLoading] = useState(false)
  const [selected, setSelected] = useState<SearchResult | null>(null)
  const [searched, setSearched] = useState(false)

  async function handleSearch() {
    if (!query.trim()) return
    setLoading(true)
    setSearched(true)
    try {
      const res = await reposApi.search(repoId, query, kind || undefined)
      setResults(res.data.results)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-4">
      {/* Search bar */}
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            className="input pl-9"
            placeholder="Search functions, classes… e.g. 'database connection handling'"
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSearch()}
          />
        </div>
        <select
          className="input w-36"
          value={kind}
          onChange={e => setKind(e.target.value)}
        >
          <option value="">All types</option>
          <option value="function">Functions</option>
          <option value="class">Classes</option>
          <option value="method">Methods</option>
        </select>
        <button className="btn-primary" onClick={handleSearch} disabled={loading}>
          {loading ? 'Searching…' : 'Search'}
        </button>
      </div>

      {/* Results + code panel */}
      <div className="grid grid-cols-2 gap-4" style={{ minHeight: 400 }}>
        {/* Results list */}
        <div className="space-y-2 overflow-y-auto max-h-[520px]">
          {!searched && (
            <p className="text-sm text-slate-600 py-8 text-center">
              Search your codebase semantically.<br />
              <span className="text-xs">Try: "authentication logic" or "database queries"</span>
            </p>
          )}
          {searched && results.length === 0 && !loading && (
            <p className="text-sm text-slate-500 py-8 text-center">No results found</p>
          )}
          {results.map(r => (
            <button
              key={r.chroma_id}
              onClick={() => setSelected(r)}
              className={`w-full text-left p-3 rounded-lg border transition-colors ${
                selected?.chroma_id === r.chroma_id
                  ? 'border-brand-500 bg-brand-900/30'
                  : 'border-slate-800 bg-surface-900 hover:border-slate-700'
              }`}
            >
              <div className="flex items-start gap-2">
                {KIND_ICON[r.kind] ?? <Code2 size={12} />}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-medium text-slate-100 truncate">{r.qualified_name}</span>
                    <span className={`badge badge-${r.kind}`}>{r.kind}</span>
                  </div>
                  <p className="text-xs text-slate-500 mt-0.5 truncate">{r.file_path}:{r.line_start}</p>
                  <pre className="text-xs text-slate-600 mt-1.5 whitespace-pre-wrap line-clamp-2 font-mono">
                    {r.snippet}
                  </pre>
                </div>
                <span className="text-xs text-slate-600 flex-shrink-0">{(r.score * 100).toFixed(0)}%</span>
              </div>
            </button>
          ))}
        </div>

        {/* Monaco code viewer */}
        <div className="card overflow-hidden">
          {selected ? (
            <>
              <div className="px-3 py-2 border-b border-slate-800 flex items-center gap-2">
                <Code2 size={12} className="text-brand-400" />
                <span className="font-mono text-xs text-slate-300">{selected.file_path}</span>
                <span className="text-xs text-slate-600">:{selected.line_start}–{selected.line_end}</span>
              </div>
              <MonacoEditor
                height="460px"
                language={monacoLanguageFor(selected.file_path)}
                value={selected.snippet}
                theme="vs-dark"
                options={{
                  readOnly: true,
                  minimap: { enabled: false },
                  scrollBeyondLastLine: false,
                  fontSize: 12,
                  lineNumbers: 'on',
                  wordWrap: 'on',
                  padding: { top: 12 },
                  fontFamily: 'JetBrains Mono, Fira Code, monospace',
                }}
              />
            </>
          ) : (
            <div className="flex items-center justify-center h-full text-slate-600 text-sm py-20">
              Select a result to view source
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
