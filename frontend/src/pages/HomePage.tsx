import { Code2, GitBranch, Search, MessageSquare, Zap } from 'lucide-react'

const FEATURES = [
  { icon: <GitBranch size={18} className="text-brand-400" />, title: 'Dependency Graph', desc: 'Visual map of how your modules import each other, powered by AST parsing and PostgreSQL recursive CTEs.' },
  { icon: <Search size={18} className="text-emerald-400" />, title: 'Semantic Search', desc: 'Find functions and classes by intent, not just name. Embeddings chunked at function/class boundaries.' },
  { icon: <MessageSquare size={18} className="text-amber-400" />, title: 'Ask Codebase', desc: 'Natural language Q&A over your codebase using LangChain RAG and gpt-4o-mini.' },
  { icon: <Zap size={18} className="text-rose-400" />, title: 'Async Ingestion', desc: 'Celery + Redis job queue with real-time progress streaming via WebSockets.' },
]

export function HomePage() {
  return (
    <div className="p-12 max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 bg-brand-600 rounded-xl flex items-center justify-center">
            <Code2 size={20} className="text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-semibold text-slate-100">Codebase Intel</h1>
            <p className="text-sm text-slate-500">Understand any GitHub repository instantly</p>
          </div>
        </div>
        <p className="text-slate-400 text-sm leading-relaxed max-w-xl">
          Add a GitHub repo. The ingestion pipeline clones it, parses every file with Python's AST module,
          builds a dependency graph in PostgreSQL, and embeds all functions and classes into ChromaDB.
          Then explore the graph, search semantically, or ask questions in plain English.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4 mb-8">
        {FEATURES.map(f => (
          <div key={f.title} className="card p-4">
            <div className="flex items-start gap-3">
              <div className="mt-0.5">{f.icon}</div>
              <div>
                <p className="text-sm font-medium text-slate-200 mb-1">{f.title}</p>
                <p className="text-xs text-slate-500 leading-relaxed">{f.desc}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="card p-4 border-brand-900">
        <p className="text-xs text-slate-500">
          <span className="text-slate-300 font-medium">Get started:</span> Click the <code className="bg-surface-800 px-1 rounded text-brand-300">+</code> button in the sidebar and paste any public GitHub URL.
        </p>
      </div>
    </div>
  )
}
