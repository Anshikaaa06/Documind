import { useState, useRef, useEffect, useCallback } from 'react'
import ChatMessage from './ChatMessage'
import SourcePanel from './SourcePanel'

const SUGGESTED_QUESTIONS = [
  'Summarise the key topics covered in this document.',
  'What are the main conclusions or recommendations?',
  'List the most important points from this document.',
]

export default function ChatInterface({ docInfo, onReset }) {
  const [messages, setMessages]       = useState([])
  const [input, setInput]             = useState('')
  const [isLoading, setIsLoading]     = useState(false)
  const [sources, setSources]         = useState([])
  const [showSources, setShowSources] = useState(false)
  const [showMobileSrc, setShowMobileSrc] = useState(false)
  const [error, setError]             = useState(null)
  const bottomRef  = useRef(null)
  const inputRef   = useRef(null)
  const textareaEl = useRef(null)

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaEl.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 120) + 'px'
  }, [input])

  // Scroll to bottom on new message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Welcome message
  useEffect(() => {
    setMessages([{
      id: 'welcome',
      role: 'assistant',
      content: `Document ready! I've processed **${docInfo.filename}** — ${docInfo.total_pages} pages split into ${docInfo.total_chunks} searchable chunks.\n\nAsk me anything about the document and I'll answer with exact page references.`,
    }])
    inputRef.current?.focus()
  }, [docInfo])

  const sendMessage = useCallback(async (text) => {
    const q = (text || input).trim()
    if (!q || isLoading) return

    setInput('')
    setError(null)

    const userMsg = { id: Date.now(),     role: 'user',      content: q }
    const loadMsg = { id: Date.now() + 1, role: 'assistant', content: '', loading: true }

    setMessages(prev => [...prev, userMsg, loadMsg])
    setIsLoading(true)
    setSources([])
    setShowSources(false)
    setShowMobileSrc(false)

    try {
      const res = await fetch('http://localhost:8000/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ doc_id: docInfo.doc_id, question: q }),
      })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.detail || `Server error (HTTP ${res.status})`)
      }
      const data = await res.json()

      setMessages(prev => prev.map(m =>
        m.id === loadMsg.id
          ? { ...m, content: data.answer, loading: false, model: data.model, usage: data.tokens_used }
          : m
      ))

      if (data.sources?.length) {
        setSources(data.sources)
        setShowSources(true)
      }

    } catch (e) {
      setMessages(prev => prev.map(m =>
        m.id === loadMsg.id
          ? { ...m, content: '', loading: false }
          : m
      ))
      // Remove the empty assistant message and show error banner instead
      setMessages(prev => prev.filter(m => m.id !== loadMsg.id))
      setError(e.message)
    } finally {
      setIsLoading(false)
    }
  }, [input, isLoading, docInfo])

  const onKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const showSuggestedQuestions = messages.length <= 1

  return (
    <div className="flex h-screen overflow-hidden">

      {/* ══════════════════════════════════
          LEFT / MAIN: Chat
      ══════════════════════════════════ */}
      <div className="flex flex-col flex-1 min-w-0 overflow-hidden">

        {/* ── Header ── */}
        <header className="shrink-0 flex items-center justify-between px-4 py-3
                            bg-surface-800/80 backdrop-blur-md border-b border-white/5 z-10">
          {/* Doc info */}
          <div className="flex items-center gap-3 min-w-0">
            <div className="shrink-0 w-8 h-8 rounded-xl bg-gradient-to-br from-brand-600 to-brand-400
                            flex items-center justify-center shadow-md shadow-brand-900/50">
              <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round"
                  d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
              </svg>
            </div>
            <div className="min-w-0">
              <p className="text-sm font-semibold text-gray-100 leading-tight truncate">
                {docInfo.filename}
              </p>
              <p className="text-xs text-gray-500">
                {docInfo.total_pages} pages · {docInfo.total_chunks} chunks
              </p>
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-1 shrink-0 ml-2">
            {/* Mobile sources button */}
            {sources.length > 0 && (
              <button
                className="md:hidden btn-ghost text-xs px-2 py-1.5"
                onClick={() => setShowMobileSrc(true)}
                aria-label="Show sources"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round"
                    d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                </svg>
                <span className="w-4 h-4 text-xs bg-brand-500 text-white rounded-full flex items-center justify-center">
                  {sources.length}
                </span>
              </button>
            )}

            {/* Desktop sources toggle */}
            {sources.length > 0 && (
              <button
                id="toggle-sources"
                onClick={() => setShowSources(v => !v)}
                className="hidden md:flex btn-ghost text-xs"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round"
                    d="M2.25 12.75V12A2.25 2.25 0 014.5 9.75h15A2.25 2.25 0 0121.75 12v.75m-8.69-6.44l-2.12-2.12a1.5 1.5 0 00-1.061-.44H4.5A2.25 2.25 0 002.25 6v12a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9a2.25 2.25 0 00-2.25-2.25h-5.379a1.5 1.5 0 01-1.06-.44z" />
                </svg>
                {showSources ? 'Hide Sources' : `Sources (${sources.length})`}
              </button>
            )}

            <button id="new-document" onClick={onReset} className="btn-ghost text-xs">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round"
                  d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" />
              </svg>
              <span className="hidden sm:inline">New Doc</span>
            </button>
          </div>
        </header>

        {/* ── Error banner ── */}
        {error && (
          <div className="mx-4 mt-3 flex items-start gap-3 p-3 rounded-xl
                          bg-red-950/60 border border-red-500/30 text-red-400 text-sm animate-fade-in">
            <svg className="w-4 h-4 mt-0.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round"
                d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
            </svg>
            <span className="flex-1">{error}</span>
            <button onClick={() => setError(null)} className="text-red-500 hover:text-red-300 transition-colors">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        )}

        {/* ── Messages ── */}
        <div className="flex-1 overflow-y-auto px-4 py-5 space-y-5">
          {messages.map(msg => (
            <ChatMessage key={msg.id} message={msg} />
          ))}

          {/* Suggested questions */}
          {showSuggestedQuestions && !isLoading && (
            <div className="flex flex-col gap-2 mt-4 animate-fade-in">
              <p className="text-xs text-gray-600 text-center">Try asking…</p>
              <div className="flex flex-wrap gap-2 justify-center">
                {SUGGESTED_QUESTIONS.map(q => (
                  <button
                    key={q}
                    onClick={() => sendMessage(q)}
                    className="px-3 py-2 rounded-xl text-xs text-gray-400 border border-white/10
                               bg-surface-700/40 hover:border-brand-500/40 hover:text-brand-300
                               hover:bg-brand-900/20 transition-all duration-200 text-left"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* ── Input bar ── */}
        <div className="shrink-0 px-4 pb-4 pt-2">
          <div className="glass p-2 flex items-end gap-2
                          focus-within:border-brand-500/30 focus-within:bg-surface-700/60
                          transition-all duration-200">
            <textarea
              id="question-input"
              ref={(el) => { inputRef.current = el; textareaEl.current = el }}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder="Ask a question about the document…"
              rows={1}
              disabled={isLoading}
              className="flex-1 bg-transparent border-none resize-none text-sm text-gray-100
                         placeholder-gray-500 focus:outline-none px-3 py-2
                         disabled:opacity-50 leading-relaxed"
              style={{ maxHeight: '120px', overflowY: 'auto' }}
            />
            <button
              id="send-button"
              onClick={() => sendMessage()}
              disabled={!input.trim() || isLoading}
              className="btn-primary shrink-0 px-4 py-2.5 self-end"
              aria-label="Send message"
            >
              {isLoading ? (
                <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth={4} />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
              ) : (
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round"
                    d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
                </svg>
              )}
            </button>
          </div>
          <p className="text-center text-xs text-gray-700 mt-1.5">
            <kbd className="px-1 py-0.5 rounded bg-surface-700 text-gray-500 font-mono text-xs">Enter</kbd> send
            &nbsp;·&nbsp;
            <kbd className="px-1 py-0.5 rounded bg-surface-700 text-gray-500 font-mono text-xs">Shift+Enter</kbd> new line
          </p>
        </div>
      </div>

      {/* ══════════════════════════════════
          RIGHT: Desktop Source Panel
      ══════════════════════════════════ */}
      {showSources && sources.length > 0 && (
        <div className="hidden md:flex">
          <SourcePanel sources={sources} onClose={() => setShowSources(false)} />
        </div>
      )}

      {/* ══════════════════════════════════
          MOBILE: Full-screen source overlay
      ══════════════════════════════════ */}
      {showMobileSrc && sources.length > 0 && (
        <div className="md:hidden fixed inset-0 z-50 bg-surface-900/95 backdrop-blur-sm animate-fade-in flex flex-col">
          <SourcePanel sources={sources} onClose={() => setShowMobileSrc(false)} />
        </div>
      )}
    </div>
  )
}
