import { useState, useRef, useEffect } from 'react'
import {
  ArrowLeft, Send, FolderTree, ChevronDown,
  FileCode, Loader2, Copy, Check, RotateCcw
} from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeHighlight from 'rehype-highlight'
import 'highlight.js/styles/github-dark.css'
import { streamChat, getModels } from '../api'

export default function ChatView({ repo, onBack }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [selectedModel, setSelectedModel] = useState('llama3.3-70b-instruct')
  const [models, setModels] = useState([])
  const [showModelPicker, setShowModelPicker] = useState(false)
  const [showSidebar, setShowSidebar] = useState(false)
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)

  // Load models
  useEffect(() => {
    getModels().then(setModels).catch(() => {})
  }, [])

  // Welcome message
  useEffect(() => {
    const langs = Object.keys(repo.language_breakdown || {}).slice(0, 5).join(', ')
    setMessages([{
      role: 'assistant',
      content: `Indexed **${repo.name}** (${repo.file_count} files${langs ? `, ${langs}` : ''}).

Ready. Some things you can ask:

- **"What does this project do?"** - high-level overview
- **"How is the project structured?"** - architecture and file organization
- **"Where is authentication handled?"** - find specific functionality
- **"Write tests for the main module"** - generate code

What would you like to know?`,
    }])
    inputRef.current?.focus()
  }, [repo])

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = async () => {
    const msg = input.trim()
    if (!msg || isStreaming) return

    const userMessage = { role: 'user', content: msg }
    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsStreaming(true)

    // Prepare history (skip welcome message)
    const history = messages
      .filter((_, i) => i > 0)
      .map(m => ({ role: m.role, content: m.content }))

    // Add streaming assistant message
    setMessages(prev => [...prev, { role: 'assistant', content: '', streaming: true }])

    try {
      let fullContent = ''
      for await (const chunk of streamChat(repo.id, msg, history, selectedModel)) {
        fullContent += chunk
        setMessages(prev => {
          const updated = [...prev]
          updated[updated.length - 1] = { role: 'assistant', content: fullContent, streaming: true }
          return updated
        })
      }

      setMessages(prev => {
        const updated = [...prev]
        updated[updated.length - 1] = { role: 'assistant', content: fullContent, streaming: false }
        return updated
      })
    } catch (err) {
      setMessages(prev => {
        const updated = [...prev]
        updated[updated.length - 1] = {
          role: 'assistant',
          content: `error: ${err.message}`,
          streaming: false,
        }
        return updated
      })
    }

    setIsStreaming(false)
    inputRef.current?.focus()
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const clearChat = () => {
    const langs = Object.keys(repo.language_breakdown || {}).slice(0, 5).join(', ')
    setMessages([{
      role: 'assistant',
      content: `Chat cleared. Still working with **${repo.name}** (${repo.file_count} files${langs ? `, ${langs}` : ''}). What would you like to explore?`,
    }])
  }

  const suggestedQuestions = [
    "What does this project do?",
    "How is the code structured?",
    "What are the main dependencies?",
    "Find potential bugs or issues",
  ]

  return (
    <div className="h-screen flex flex-col bg-black">
      {/* Header */}
      <header className="border-b border-terminal-border bg-black px-4 py-2 flex items-center justify-between shrink-0 font-mono">
        <div className="flex items-center gap-3 text-sm">
          <button onClick={onBack} className="p-1.5 hover:bg-terminal-surface transition-colors text-terminal-muted hover:text-white">
            <ArrowLeft className="w-4 h-4" />
          </button>
          <span className="text-terminal-accent font-bold">REPOWHISPERER</span>
          <span className="text-terminal-border">|</span>
          <a href={repo.url} target="_blank" rel="noopener noreferrer" className="text-terminal-muted hover:text-white transition-colors text-xs">
            {repo.name}
          </a>
          <span className="text-terminal-border text-xs">[{repo.file_count} files]</span>
        </div>

        <div className="flex items-center gap-1">
          {/* Model picker */}
          <div className="relative">
            <button
              onClick={() => setShowModelPicker(!showModelPicker)}
              className="flex items-center gap-1.5 px-2 py-1 border border-terminal-border text-xs text-terminal-muted hover:text-white hover:border-terminal-accent transition-colors font-mono"
            >
              {selectedModel.split('/').pop()}
              <ChevronDown className="w-3 h-3" />
            </button>
            {showModelPicker && (
              <div className="absolute right-0 top-full mt-1 w-64 bg-black border border-terminal-border shadow-2xl z-50">
                {models.map((model) => (
                  <button
                    key={model.id}
                    onClick={() => { setSelectedModel(model.id); setShowModelPicker(false) }}
                    className={`w-full px-3 py-2 text-left hover:bg-terminal-surface transition-colors font-mono text-xs ${
                      selectedModel === model.id ? 'text-terminal-accent' : 'text-terminal-muted'
                    }`}
                  >
                    <div>{model.name}</div>
                    <div className="text-terminal-border text-xs">{model.provider}</div>
                  </button>
                ))}
              </div>
            )}
          </div>

          <button onClick={clearChat} className="p-1.5 hover:bg-terminal-surface transition-colors text-terminal-muted hover:text-white" title="Clear chat">
            <RotateCcw className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={() => setShowSidebar(!showSidebar)}
            className={`p-1.5 hover:bg-terminal-surface transition-colors ${showSidebar ? 'text-terminal-accent' : 'text-terminal-muted hover:text-white'}`}
            title="File tree"
          >
            <FolderTree className="w-3.5 h-3.5" />
          </button>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* Chat area */}
        <div className="flex-1 flex flex-col">
          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-4 py-6">
            <div className="max-w-3xl mx-auto space-y-4">
              {messages.map((msg, i) => (
                <MessageBlock key={i} message={msg} />
              ))}

              {/* Suggested questions */}
              {messages.length === 1 && !isStreaming && (
                <div className="flex flex-wrap gap-2 ml-6">
                  {suggestedQuestions.map((q) => (
                    <button
                      key={q}
                      onClick={() => { setInput(q); setTimeout(() => inputRef.current?.focus(), 50) }}
                      className="px-2 py-1 text-xs font-mono border border-terminal-border text-terminal-muted hover:text-terminal-accent hover:border-terminal-accent transition-colors"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          </div>

          {/* Input */}
          <div className="border-t border-terminal-border bg-black px-4 py-3 shrink-0">
            <div className="max-w-3xl mx-auto">
              <div className="flex items-end gap-2 font-mono">
                <span className="text-terminal-accent py-3 select-none">{'>'}</span>
                <textarea
                  ref={inputRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder={isStreaming ? 'waiting for response...' : 'ask about the codebase...'}
                  disabled={isStreaming}
                  rows={1}
                  className="flex-1 py-3 bg-transparent text-white placeholder-terminal-muted focus:outline-none resize-none disabled:opacity-50 text-sm font-mono"
                  style={{ minHeight: '24px', maxHeight: '150px' }}
                  onInput={(e) => {
                    e.target.style.height = 'auto'
                    e.target.style.height = Math.min(e.target.scrollHeight, 150) + 'px'
                  }}
                />
                <button
                  onClick={handleSend}
                  disabled={isStreaming || !input.trim()}
                  className="p-2 text-terminal-accent hover:text-orange-400 disabled:text-terminal-border disabled:cursor-not-allowed transition-colors shrink-0"
                >
                  {isStreaming ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Send className="w-4 h-4" />
                  )}
                </button>
              </div>
              <p className="text-center text-terminal-border text-xs mt-1 font-mono">
                {selectedModel.split('/').pop()}
              </p>
            </div>
          </div>
        </div>

        {/* Sidebar - File tree */}
        {showSidebar && (
          <div className="w-72 border-l border-terminal-border bg-black overflow-y-auto p-4 font-mono">
            <h3 className="text-xs font-bold text-terminal-accent mb-3 flex items-center gap-2">
              <FolderTree className="w-3.5 h-3.5" />
              STRUCTURE
            </h3>
            {repo.description ? (
              <pre className="text-xs text-terminal-muted whitespace-pre-wrap leading-relaxed">
                {repo.description}
              </pre>
            ) : (
              <p className="text-xs text-terminal-border">loading...</p>
            )}

            {repo.language_breakdown && Object.keys(repo.language_breakdown).length > 0 && (
              <div className="mt-6">
                <h3 className="text-xs font-bold text-terminal-accent mb-3 flex items-center gap-2">
                  <FileCode className="w-3.5 h-3.5" />
                  LANGUAGES
                </h3>
                <div className="space-y-1">
                  {Object.entries(repo.language_breakdown).map(([lang, count]) => (
                    <div key={lang} className="flex items-center justify-between text-xs">
                      <span className="text-terminal-muted">{lang}</span>
                      <span className="text-terminal-border">{count}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Click outside to close model picker */}
      {showModelPicker && (
        <div className="fixed inset-0 z-40" onClick={() => setShowModelPicker(false)} />
      )}
    </div>
  )
}

function MessageBlock({ message }) {
  const [copied, setCopied] = useState(false)
  const isUser = message.role === 'user'

  const copyContent = () => {
    navigator.clipboard.writeText(message.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="group font-mono">
      {/* Label */}
      <div className="flex items-center gap-2 mb-1">
        <span className={`text-xs font-bold ${isUser ? 'text-white' : 'text-terminal-accent'}`}>
          {isUser ? '> you' : '> repowhisperer'}
        </span>
        {!isUser && !message.streaming && message.content && (
          <button
            onClick={copyContent}
            className="p-0.5 opacity-0 group-hover:opacity-100 transition-opacity text-terminal-muted hover:text-white"
          >
            {copied ? <Check className="w-3 h-3 text-green-500" /> : <Copy className="w-3 h-3" />}
          </button>
        )}
      </div>

      {/* Content */}
      <div className="pl-4 border-l border-terminal-border">
        {isUser ? (
          <p className="text-sm text-terminal-text whitespace-pre-wrap">{message.content}</p>
        ) : (
          <div className={`prose prose-invert prose-sm prose-terminal max-w-none text-sm ${message.streaming ? 'typing-cursor' : ''}`}>
            <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>
              {message.content}
            </ReactMarkdown>
          </div>
        )}
      </div>
    </div>
  )
}
