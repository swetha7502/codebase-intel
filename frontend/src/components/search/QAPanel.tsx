import { useState } from 'react'
import { MessageSquare, Send, FileCode, Loader2 } from 'lucide-react'
import { reposApi } from '../../lib/api'

interface Message {
  role: 'user' | 'assistant'
  content: string
  sources?: any[]
}

interface Props { repoId: string }

const SUGGESTIONS = [
  'How does the main entry point work?',
  'Where is database connection handled?',
  'What does the ingestion pipeline do?',
  'How are imports resolved?',
]

export function QAPanel({ repoId }: Props) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)

  async function sendMessage(text: string) {
    const question = text.trim()
    if (!question) return
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: question }])
    setLoading(true)
    try {
      const res = await reposApi.qa(repoId, question)
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: res.data.answer,
        sources: res.data.sources,
      }])
    } catch {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Error: could not get an answer.' }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col h-[600px]">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-4 pb-4">
        {messages.length === 0 && (
          <div className="py-8">
            <p className="text-sm text-slate-500 text-center mb-4">Ask anything about this codebase</p>
            <div className="grid grid-cols-2 gap-2">
              {SUGGESTIONS.map(s => (
                <button
                  key={s}
                  onClick={() => sendMessage(s)}
                  className="text-left text-xs text-slate-400 border border-slate-800 rounded-lg px-3 py-2.5 hover:border-brand-500 hover:text-slate-200 transition-colors"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[80%] ${msg.role === 'user' ? 'order-1' : 'order-2'}`}>
              {msg.role === 'user' ? (
                <div className="bg-brand-600 text-white rounded-2xl rounded-tr-sm px-4 py-2.5 text-sm">
                  {msg.content}
                </div>
              ) : (
                <div className="space-y-2">
                  <div className="bg-surface-900 border border-slate-800 rounded-2xl rounded-tl-sm px-4 py-3 text-sm text-slate-200 whitespace-pre-wrap">
                    {msg.content}
                  </div>
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="flex flex-wrap gap-1.5">
                      {msg.sources.filter(s => s.file_path).slice(0, 4).map((s, j) => (
                        <span key={j} className="flex items-center gap-1 text-xs text-slate-500 bg-surface-800 border border-slate-700 rounded px-2 py-1">
                          <FileCode size={10} />
                          <span className="font-mono">{s.file_path?.split('/').pop()}:{s.line_start}</span>
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-surface-900 border border-slate-800 rounded-2xl rounded-tl-sm px-4 py-3">
              <Loader2 size={14} className="animate-spin text-brand-400" />
            </div>
          </div>
        )}
      </div>

      {/* Input */}
      <div className="border-t border-slate-800 pt-4">
        <div className="flex gap-2">
          <input
            className="input flex-1"
            placeholder="Ask about this codebase…"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && !loading && sendMessage(input)}
            disabled={loading}
          />
          <button
            className="btn-primary px-3"
            onClick={() => sendMessage(input)}
            disabled={loading || !input.trim()}
          >
            <Send size={14} />
          </button>
        </div>
      </div>
    </div>
  )
}
