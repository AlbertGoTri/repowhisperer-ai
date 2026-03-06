import { useState, useRef, useEffect } from 'react'
import {
  ArrowLeft, Send, Code2, FolderTree, ChevronDown,
  FileCode, Loader2, Bot, User, Copy, Check, RotateCcw
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
      content: `👋 Hey! I've indexed **${repo.name}** (${repo.file_count} files${langs ? ` — ${langs}` : ''}).

I'm ready to help you explore this codebase. Here are some things you can ask me:

- **"What does this project do?"** — I'll give you a high-level overview
- **"How is the project structured?"** — Architecture and file organization
- **"Where is authentication handled?"** — Find specific functionality
- **"Write tests for the main module"** — Generate code
- **"What are potential improvements?"** — Code review and suggestions

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
      .filter((_, i) => i > 0) // skip welcome
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

      // Mark as done
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
          content: `❌ Error: ${err.message}. Make sure your DigitalOcean Gradient AI key is configured.`,
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
      content: `🔄 Chat cleared! Still working with **${repo.name}** (${repo.file_count} files${langs ? ` — ${langs}` : ''}). What would you like to explore?`,
    }])
  }

  const suggestedQuestions = [
    "What does this project do?",
    "How is the code structured?",
    "What are the main dependencies?",
    "Find potential bugs or issues",
  ]

  return (
    <div className="h-screen flex flex-col">
      {/* Header */}
      <header className="border-b border-slate-800 bg-[#0d1221] px-4 py-3 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <button onClick={onBack} className="p-2 hover:bg-slate-800 rounded-lg transition-colors text-slate-400 hover:text-white">
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div className="flex items-center gap-2">
            <Code2 className="w-5 h-5 text-ocean-400" />
            <span className="font-semibold text-white">RepoWhisperer</span>
          </div>
          <span className="text-slate-600">·</span>
          <a href={repo.url} target="_blank" rel="noopener noreferrer" className="text-ocean-400 hover:text-ocean-300 text-sm font-mono transition-colors">
            {repo.name}
          </a>
          <span className="px-2 py-0.5 bg-ocean-900/50 text-ocean-400 text-xs rounded-full">
            {repo.file_count} files
          </span>
        </div>

        <div className="flex items-center gap-2">
          {/* Model picker */}
          <div className="relative">
            <button
              onClick={() => setShowModelPicker(!showModelPicker)}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-[#131829] border border-slate-700 rounded-lg text-sm text-slate-300 hover:border-slate-600 transition-colors"
            >
              {selectedModel.split('/').pop()}
              <ChevronDown className="w-3.5 h-3.5" />
            </button>
            {showModelPicker && (
              <div className="absolute right-0 top-full mt-1 w-64 bg-[#131829] border border-slate-700 rounded-xl shadow-2xl z-50 overflow-hidden">
                {models.map((model) => (
                  <button
                    key={model.id}
                    onClick={() => { setSelectedModel(model.id); setShowModelPicker(false) }}
                    className={`w-full px-4 py-3 text-left hover:bg-slate-800 transition-colors ${
                      selectedModel === model.id ? 'bg-ocean-900/30 text-ocean-300' : 'text-slate-300'
                    }`}
                  >
                    <div className="font-medium text-sm">{model.name}</div>
                    <div className="text-xs text-slate-500">{model.provider}</div>
                  </button>
                ))}
              </div>
            )}
          </div>

          <button onClick={clearChat} className="p-2 hover:bg-slate-800 rounded-lg transition-colors text-slate-400 hover:text-white" title="Clear chat">
            <RotateCcw className="w-4 h-4" />
          </button>

          <button
            onClick={() => setShowSidebar(!showSidebar)}
            className="p-2 hover:bg-slate-800 rounded-lg transition-colors text-slate-400 hover:text-white"
            title="File tree"
          >
            <FolderTree className="w-4 h-4" />
          </button>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* Chat area */}
        <div className="flex-1 flex flex-col">
          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-4 py-6">
            <div className="max-w-3xl mx-auto space-y-6">
              {messages.map((msg, i) => (
                <MessageBubble key={i} message={msg} />
              ))}

              {/* Suggested questions (show only after welcome message) */}
              {messages.length === 1 && !isStreaming && (
                <div className="flex flex-wrap gap-2 ml-12">
                  {suggestedQuestions.map((q) => (
                    <button
                      key={q}
                      onClick={() => { setInput(q); setTimeout(() => inputRef.current?.focus(), 50) }}
                      className="px-3 py-2 text-sm bg-[#131829] border border-slate-700 rounded-xl text-slate-400 hover:text-ocean-400 hover:border-ocean-700 transition-colors"
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
          <div className="border-t border-slate-800 bg-[#0d1221] px-4 py-4 shrink-0">
            <div className="max-w-3xl mx-auto">
              <div className="relative flex items-end gap-2">
                <textarea
                  ref={inputRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder={isStreaming ? 'Waiting for response...' : 'Ask about the codebase...'}
                  disabled={isStreaming}
                  rows={1}
                  className="flex-1 px-4 py-3 bg-[#131829] border border-slate-700 rounded-2xl text-white placeholder-slate-500 focus:outline-none input-glow transition-all resize-none disabled:opacity-50"
                  style={{ minHeight: '48px', maxHeight: '150px' }}
                  onInput={(e) => {
                    e.target.style.height = 'auto'
                    e.target.style.height = Math.min(e.target.scrollHeight, 150) + 'px'
                  }}
                />
                <button
                  onClick={handleSend}
                  disabled={isStreaming || !input.trim()}
                  className="p-3 bg-ocean-500 hover:bg-ocean-600 disabled:bg-slate-700 disabled:cursor-not-allowed text-white rounded-xl transition-colors shrink-0"
                >
                  {isStreaming ? (
                    <Loader2 className="w-5 h-5 animate-spin" />
                  ) : (
                    <Send className="w-5 h-5" />
                  )}
                </button>
              </div>
              <p className="text-center text-slate-600 text-xs mt-2">
                Powered by DigitalOcean Gradient™ AI · Model: {selectedModel.split('/').pop()}
              </p>
            </div>
          </div>
        </div>

        {/* Sidebar - File tree */}
        {showSidebar && (
          <div className="w-80 border-l border-slate-800 bg-[#0d1221] overflow-y-auto p-4">
            <h3 className="text-sm font-semibold text-slate-300 mb-3 flex items-center gap-2">
              <FolderTree className="w-4 h-4 text-ocean-400" />
              Project Structure
            </h3>
            {repo.description ? (
              <pre className="text-xs text-slate-400 font-mono whitespace-pre-wrap leading-relaxed">
                {repo.description}
              </pre>
            ) : (
              <p className="text-sm text-slate-500">Structure loading...</p>
            )}

            {repo.language_breakdown && Object.keys(repo.language_breakdown).length > 0 && (
              <div className="mt-6">
                <h3 className="text-sm font-semibold text-slate-300 mb-3 flex items-center gap-2">
                  <FileCode className="w-4 h-4 text-ocean-400" />
                  Languages
                </h3>
                <div className="space-y-2">
                  {Object.entries(repo.language_breakdown).map(([lang, count]) => (
                    <div key={lang} className="flex items-center justify-between text-sm">
                      <span className="text-slate-400">{lang}</span>
                      <span className="text-slate-500 font-mono text-xs">{count} files</span>
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

function MessageBubble({ message }) {
  const [copied, setCopied] = useState(false)
  const isUser = message.role === 'user'

  const copyContent = () => {
    navigator.clipboard.writeText(message.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className={`flex gap-3 ${isUser ? 'justify-end' : ''}`}>
      {!isUser && (
        <div className="w-8 h-8 bg-ocean-900/50 rounded-lg flex items-center justify-center shrink-0 mt-1">
          <Bot className="w-4 h-4 text-ocean-400" />
        </div>
      )}

      <div className={`group relative max-w-[85%] ${
        isUser
          ? 'bg-ocean-600/20 border border-ocean-800 rounded-2xl rounded-tr-md px-4 py-3'
          : 'flex-1'
      }`}>
        {isUser ? (
          <p className="text-slate-200 whitespace-pre-wrap">{message.content}</p>
        ) : (
          <div className={`prose prose-invert prose-sm max-w-none ${message.streaming ? 'typing-cursor' : ''}`}>
            <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>
              {message.content}
            </ReactMarkdown>
          </div>
        )}

        {/* Copy button */}
        {!isUser && !message.streaming && message.content && (
          <button
            onClick={copyContent}
            className="absolute -right-2 top-0 p-1.5 bg-slate-800 border border-slate-700 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity text-slate-400 hover:text-white"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-green-400" /> : <Copy className="w-3.5 h-3.5" />}
          </button>
        )}
      </div>

      {isUser && (
        <div className="w-8 h-8 bg-slate-800 rounded-lg flex items-center justify-center shrink-0 mt-1">
          <User className="w-4 h-4 text-slate-400" />
        </div>
      )}
    </div>
  )
}
