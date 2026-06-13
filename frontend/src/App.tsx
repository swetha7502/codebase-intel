import { useState, useEffect } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Sidebar } from './components/layout/Sidebar'
import { HomePage } from './pages/HomePage'
import { RepoPage } from './pages/RepoPage'
import { reposApi, Repo } from './lib/api'

export default function App() {
  const [repos, setRepos] = useState<Repo[]>([])

  const loadRepos = async () => {
    try {
      const res = await reposApi.list()
      setRepos(res.data.items)
    } catch {}
  }

  useEffect(() => { loadRepos() }, [])

  return (
    <BrowserRouter>
      <div className="flex h-screen overflow-hidden">
        <Sidebar
          repos={repos}
          onRepoAdded={loadRepos}
          onRepoDeleted={id => setRepos(prev => prev.filter(r => r.id !== id))}
        />
        <main className="flex-1 overflow-y-auto">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/repo/:id" element={<RepoPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
