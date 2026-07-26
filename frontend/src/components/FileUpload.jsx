import { useState, useRef, useCallback } from 'react'

const ACCEPTED_TYPE = 'application/pdf'
const MAX_MB = 20

export default function FileUpload({ onUploadSuccess, isUploading, setIsUploading }) {
  const [dragOver, setDragOver] = useState(false)
  const [error, setError]       = useState(null)
  const inputRef = useRef(null)

  const validate = (file) => {
    if (!file) return 'No file selected.'
    if (file.type !== ACCEPTED_TYPE && !file.name.endsWith('.pdf'))
      return 'Only PDF files are supported.'
    if (file.size > MAX_MB * 1024 * 1024)
      return `File is too large (${(file.size / 1024 / 1024).toFixed(1)} MB). Max: ${MAX_MB} MB.`
    return null
  }

  const handleFile = useCallback(async (file) => {
    const err = validate(file)
    if (err) { setError(err); return }
    setError(null)
    setIsUploading(true)

    const formData = new FormData()
    formData.append('file', file)

    try {
      const res = await fetch('http://localhost:8000/api/upload', {
        method: 'POST',
        body: formData,
      })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.detail || `Upload failed (HTTP ${res.status})`)
      }
      const data = await res.json()
      onUploadSuccess(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setIsUploading(false)
    }
  }, [onUploadSuccess, setIsUploading])

  const onDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files[0]
    if (file) handleFile(file)
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-screen px-4 animate-fade-in">
      {/* Logo / Hero */}
      <div className="mb-10 text-center">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl
                        bg-gradient-to-br from-brand-600 to-brand-400 mb-4 shadow-xl shadow-brand-900/50">
          <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
            <path strokeLinecap="round" strokeLinejoin="round"
              d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25zM6.75 12h.008v.008H6.75V12zm0 3h.008v.008H6.75V15zm0 3h.008v.008H6.75V18z" />
          </svg>
        </div>
        <h1 className="text-4xl font-bold bg-gradient-to-r from-white to-gray-400 bg-clip-text text-transparent">
          DocuMind
        </h1>
        <p className="mt-2 text-gray-400 text-lg">
          AI-powered document research assistant
        </p>
        <p className="mt-1 text-gray-500 text-sm">
          Upload a PDF and ask questions — get answers with exact page citations
        </p>
      </div>

      {/* Drop zone */}
      <div
        onDrop={onDrop}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onClick={() => !isUploading && inputRef.current?.click()}
        className={`
          glass w-full max-w-lg p-10 flex flex-col items-center gap-4
          cursor-pointer transition-all duration-300 group
          ${dragOver ? 'border-brand-500/60 bg-brand-900/20 scale-[1.02]' : 'hover:border-white/15 hover:bg-surface-700/50'}
          ${isUploading ? 'pointer-events-none' : ''}
        `}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,application/pdf"
          className="hidden"
          onChange={(e) => e.target.files[0] && handleFile(e.target.files[0])}
        />

        {isUploading ? (
          <>
            <div className="w-14 h-14 rounded-full border-4 border-surface-600 border-t-brand-500 animate-spin-slow" />
            <p className="text-gray-300 font-medium">Processing your document…</p>
            <p className="text-gray-500 text-sm">Chunking, embedding, and indexing</p>
          </>
        ) : (
          <>
            <div className={`
              w-14 h-14 rounded-2xl flex items-center justify-center transition-all duration-300
              ${dragOver ? 'bg-brand-500/20 scale-110' : 'bg-surface-600/50 group-hover:bg-brand-900/40'}
            `}>
              <svg className={`w-7 h-7 transition-colors duration-300 ${dragOver ? 'text-brand-400' : 'text-gray-400 group-hover:text-brand-400'}`}
                fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round"
                  d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
              </svg>
            </div>
            <div className="text-center">
              <p className="text-gray-200 font-semibold">
                {dragOver ? 'Drop your PDF here' : 'Drop PDF here or click to browse'}
              </p>
              <p className="text-gray-500 text-sm mt-1">PDF files only · Max {MAX_MB} MB</p>
            </div>
            <button className="btn-primary mt-2" onClick={(e) => { e.stopPropagation(); inputRef.current?.click() }}>
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
              </svg>
              Choose File
            </button>
          </>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="mt-4 w-full max-w-lg flex items-start gap-3 p-4 rounded-xl
                        bg-red-950/60 border border-red-500/30 text-red-400 text-sm animate-fade-in">
          <svg className="w-4 h-4 mt-0.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
          </svg>
          {error}
        </div>
      )}

      {/* Feature pills */}
      <div className="mt-10 flex flex-wrap gap-3 justify-center">
        {['Page-accurate citations', 'Local AI embeddings', 'Groq LLM (free)', 'ChromaDB vector search'].map(f => (
          <span key={f} className="px-3 py-1.5 rounded-full text-xs font-medium
                                    bg-surface-700/60 text-gray-400 border border-white/5">
            {f}
          </span>
        ))}
      </div>
    </div>
  )
}
