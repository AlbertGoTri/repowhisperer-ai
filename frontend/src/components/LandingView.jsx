import { useState, useEffect } from 'react'
import { Github, Loader2, ArrowRight, Code2, MessageSquare, Zap, Search } from 'lucide-react'
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
          setError('Failed to index repository. Please check the URL and try again.')
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
    <div className="min-h-screen flex flex-col items-center justify-center px-4">
      {/* Header */}
      <div className="text-center mb-12">
        <div className="flex items-center justify-center gap-3 mb-4">
          <div className="w-12 h-12 bg-ocean-500 rounded-xl flex items-center justify-center">
            <Code2 className="w-7 h-7 text-white" />
          </div>
          <h1 className="text-4xl font-bold text-white">
            Repo<span className="text-ocean-400">Whisperer</span>
          </h1>
        </div>
        <p className="text-lg text-slate-400 max-w-lg mx-auto">
          Paste a GitHub repo URL and chat with your codebase.
          Understand architecture, find code, generate tests — powered by AI.
        </p>
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="w-full max-w-2xl mb-8">
        <div className="relative">
          <Github className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
          <input
            type="url"
            value={repoUrl}
            onChange={(e) => setRepoUrl(e.target.value)}
            placeholder="https://github.com/owner/repo"
            disabled={loading}
            className="w-full pl-12 pr-32 py-4 bg-[#131829] border border-slate-700 rounded-2xl text-white placeholder-slate-500 focus:outline-none input-glow transition-all text-lg disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={loading || !repoUrl.trim()}
            className="absolute right-2 top-1/2 -translate-y-1/2 px-6 py-2.5 bg-ocean-500 hover:bg-ocean-600 disabled:bg-slate-700 disabled:cursor-not-allowed text-white font-medium rounded-xl transition-colors flex items-center gap-2"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                {indexingRepo ? 'Indexing...' : 'Loading...'}
              </>
            ) : (
              <>
                Explore <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </div>
        {error && (
          <p className="mt-3 text-red-400 text-sm text-center">{error}</p>
        )}

        {/* Indexing progress */}
        {indexingRepo && (
          <div className="mt-4 p-4 bg-[#131829] border border-ocean-800 rounded-xl">
            <div className="flex items-center gap-3">
              <div className="w-2 h-2 bg-ocean-400 rounded-full pulse-dot" />
              <span className="text-ocean-300 text-sm">
                Cloning and indexing <span className="font-mono text-ocean-200">{indexingRepo.name}</span>...
              </span>
            </div>
            <p className="text-slate-500 text-xs mt-2 ml-5">
              This usually takes 10-30 seconds depending on repo size.
            </p>
          </div>
        )}
      </form>

      {/* Example repos */}
      <div className="flex flex-wrap gap-2 justify-center mb-16">
        <span className="text-slate-500 text-sm mr-1">Try:</span>
        {exampleRepos.map((repo) => (
          <button
            key={repo.url}
            onClick={() => setRepoUrl(repo.url)}
            className="px-3 py-1.5 text-sm bg-[#131829] border border-slate-700 rounded-lg text-slate-400 hover:text-ocean-400 hover:border-ocean-700 transition-colors font-mono"
          >
            {repo.name}
          </button>
        ))}
      </div>

      {/* Features */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-4xl w-full">
        <FeatureCard
          icon={<Search className="w-6 h-6" />}
          title="Understand"
          description="Ask about architecture, patterns, and how any part of the code works."
        />
        <FeatureCard
          icon={<MessageSquare className="w-6 h-6" />}
          title="Chat"
          description="Have a conversation about the code. Get explanations, find bugs, explore."
        />
        <FeatureCard
          icon={<Zap className="w-6 h-6" />}
          title="Generate"
          description="Create tests, refactor code, write docs — all matching the repo's style."
        />
      </div>

      {/* Footer */}
      <div className="mt-16 mb-8 text-center">
        <p className="text-slate-600 text-sm">
          Powered by{' '}
          <a href="https://www.digitalocean.com/products/gradient/platform" target="_blank" rel="noopener noreferrer" className="text-ocean-500 hover:text-ocean-400 transition-colors">
            DigitalOcean Gradient™ AI
          </a>
        </p>
      </div>
    </div>
  )
}

function FeatureCard({ icon, title, description }) {
  return (
    <div className="p-6 bg-[#131829] border border-slate-800 rounded-2xl hover:border-slate-700 transition-colors">
      <div className="w-10 h-10 bg-ocean-900/50 rounded-lg flex items-center justify-center text-ocean-400 mb-4">
        {icon}
      </div>
      <h3 className="text-white font-semibold mb-2">{title}</h3>
      <p className="text-slate-400 text-sm leading-relaxed">{description}</p>
    </div>
  )
}
