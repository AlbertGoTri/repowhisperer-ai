import { useState } from 'react'
import LandingView from './components/LandingView'
import ChatView from './components/ChatView'

export default function App() {
  const [activeRepo, setActiveRepo] = useState(null)

  return (
    <div className="min-h-screen bg-[#0a0e1a]">
      {activeRepo ? (
        <ChatView repo={activeRepo} onBack={() => setActiveRepo(null)} />
      ) : (
        <LandingView onRepoReady={(repo) => setActiveRepo(repo)} />
      )}
    </div>
  )
}
