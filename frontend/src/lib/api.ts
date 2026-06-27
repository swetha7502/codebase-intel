import axios from 'axios'
export const api = axios.create({ baseURL: `${import.meta.env.VITE_API_URL}/v1` })

export interface Repo {
  id: string
  github_url: string
  owner: string
  name: string
  default_branch: string
  description?: string | null
  language?: string | null
  star_count: number
  status: string
  file_count: number
  function_count: number
  class_count: number
  error_message?: string | null
  created_at: string
  updated_at: string
}

export interface GraphNode { id: string; label: string; language: string; line_count: number; symbol_count: number }
export interface GraphEdge { source: string; target: string; module_name: string }
export interface DependencyGraph { nodes: GraphNode[]; edges: GraphEdge[] }

export interface SearchResult {
  chroma_id: string
  file_path: string
  qualified_name: string
  kind: string
  line_start: number
  line_end: number
  score: number
  snippet: string
}

export interface Symbol {
  id: string
  name: string
  qualified_name: string
  kind: string
  line_start: number | null
  line_end: number | null
  docstring: string | null
  source_code: string | null
  file_path: string
}

export const reposApi = {
  list: () => api.get<{ items: Repo[]; total: number }>('/repositories'),
  add: (github_url: string) => api.post<Repo>('/repositories', { github_url }),
  get: (id: string) => api.get<Repo>(`/repositories/${id}`),
  delete: (id: string) => api.delete(`/repositories/${id}`),
  reindex: (id: string) => api.post<Repo>(`/repositories/${id}/reindex`),
  graph: (id: string) => api.get<DependencyGraph>(`/repositories/${id}/graph`),
  symbols: (id: string, page = 1, kind?: string) =>
    api.get<{ items: Symbol[]; total: number; page: number; page_size: number }>(
      `/repositories/${id}/symbols`,
      { params: { page, ...(kind ? { kind } : {}) } }
    ),
  search: (id: string, q: string, kind?: string) =>
    api.get<{ results: SearchResult[]; total: number; query: string }>(
      `/repositories/${id}/search`,
      { params: { q, ...(kind ? { kind } : {}) } }
    ),
  qa: (id: string, question: string) =>
    api.post<{ answer: string; sources: any[] }>(`/repositories/${id}/qa`, { question }),
}
