import { useState, useEffect } from 'react'
import { Loader2 } from 'lucide-react'
import { indexRepo, getRepo } from '../api'

export default function LandingView({ onRepoReady }) {
  const [repoUrl, setRepoUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [indexingRepo, setIndexingRepo] = useState(null)
  const [error, setError] = useState('')

  // Poll for indexing status
  useEffect(() => {
    if (!indexingRepo) return
    const interval = setInterval(async () => {
      try {
        const repo = await getRepo(indexingRepo.id)
        if (repo.status === 'ready') {
          clearInterval(interval)
          onRepoReady(repo)
        } else if (repo.status === 'error') {
          clearInterval(interval)
          setError('Failed to index repository. Check the URL and try again.')
          setIndexingRepo(null)
          setLoading(false)
        }
      } catch {
        // Keep polling
      }
    }, 2000)
    return () => clearInterval(interval)
  }, [indexingRepo, onRepoReady])

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!repoUrl.trim()) return

    setError('')
    setLoading(true)

    try {
      const repo = await indexRepo(repoUrl.trim())
      if (repo.status === 'ready') {
        onRepoReady(repo)
      } else {
        setIndexingRepo(repo)
      }
    } catch (err) {
      setError(err.message)
      setLoading(false)
    }
  }

  const exampleRepos = [
    { name: 'fastapi/fastapi', url: 'https://github.com/fastapi/fastapi' },
    { name: 'expressjs/express', url: 'https://github.com/expressjs/express' },
    { name: 'pallets/flask', url: 'https://github.com/pallets/flask' },
  ]

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4 bg-black">
      {/* Title */}
      <div className="text-center mb-10">
        <h1 className="text-5xl font-bold tracking-tight mb-3">
          <span className="text-terminal-accent">REPO</span>
          <span className="text-white">WHISPERER</span>
        </h1>
        <p className="text-terminal-muted font-mono text-sm">
          paste a github repo url. chat with the codebase.
        </p>
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="w-full max-w-2xl mb-6">
        <div className="flex items-center border border-terminal-border bg-black font-mono">
          <span className="text-terminal-accent pl-4 pr-2 select-none">{'>'}</span>
          <input
            type="url"
            value={repoUrl}
            onChange={(e) => setRepoUrl(e.target.value)}
            placeholder="https://github.com/owner/repo"
            disabled={loading}
            className="flex-1 py-3 bg-transparent text-white placeholder-terminal-muted focus:outline-none text-sm disabled:opacity-50 font-mono"
          />
          <button
            type="submit"
            disabled={loading || !repoUrl.trim()}
            className="px-5 py-3 bg-terminal-accent hover:bg-orange-600 disabled:bg-terminal-border disabled:text-terminal-muted text-black font-mono font-semibold text-sm transition-colors"
          >
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              'INDEX'
            )}
          </button>
        </div>
        {error && (
          <p className="mt-2 text-red-500 text-xs font-mono">{error}</p>
        )}

        {/* Indexing progress */}
        {indexingRepo && (
          <div className="mt-3 px-4 py-3 border border-terminal-border font-mono text-xs">
            <div className="flex items-center gap-2">
              <span className="text-terminal-accent pulse-dot inline-block w-1.5 h-1.5 bg-terminal-accent rounded-full" />
              <span className="text-terminal-muted">
                cloning and indexing <span className="text-white">{indexingRepo.name}</span> ...
              </span>
            </div>
          </div>
        )}
      </form>

      {/* Example repos */}
      <div className="flex flex-wrap gap-2 justify-center mb-16 font-mono">
        <span className="text-terminal-muted text-xs">try:</span>
        {exampleRepos.map((repo) => (
          <button
            key={repo.url}
            onClick={() => setRepoUrl(repo.url)}
            className="px-2 py-1 text-xs border border-terminal-border text-terminal-muted hover:text-terminal-accent hover:border-terminal-accent transition-colors"
          >
            {repo.name}
          </button>
        ))}
      </div>

      {/* Features */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-px max-w-3xl w-full border border-terminal-border">
        <FeatureBlock title="UNDERSTAND" desc="ask about architecture, patterns, and how the code works." />
        <FeatureBlock title="SEARCH" desc="find where specific functionality is implemented." />
        <FeatureBlock title="GENERATE" desc="create tests, refactors, and docs matching the repo style." />
      </div>

      {/* Footer */}
      <div className="mt-12 mb-8 text-center">
        <p className="text-terminal-muted text-xs font-mono">
          powered by{' '}
          <a href="https://www.digitalocean.com/products/gradient/platform" target="_blank" rel="noopener noreferrer" className="text-terminal-accent hover:underline">
            DigitalOcean Gradient AI
          </a>
        </p>
      </div>
    </div>
  )
}

function FeatureBlock({ title, desc }) {
  return (
    <div className="p-5 border border-terminal-border bg-black">
      <h3 className="text-terminal-accent font-mono font-bold text-xs mb-2">{title}</h3>
      <p className="text-terminal-muted font-mono text-xs leading-relaxed">{desc}</p>
    </div>
  )
}
