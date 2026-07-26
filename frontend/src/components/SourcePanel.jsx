import SourceCard from './SourceCard'

export default function SourcePanel({ sources, onClose }) {
  if (!sources || sources.length === 0) return null

  return (
    <aside
      className="flex flex-col w-full md:w-80 shrink-0 border-l border-white/5
                 bg-surface-800/50 backdrop-blur-sm overflow-hidden animate-fade-in"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/5">
        <div>
          <h2 className="text-sm font-semibold text-gray-200">Source Excerpts</h2>
          <p className="text-xs text-gray-500 mt-0.5">
            {sources.length} chunk{sources.length !== 1 ? 's' : ''} retrieved
          </p>
        </div>
        <button
          onClick={onClose}
          className="btn-ghost p-1.5 rounded-lg"
          aria-label="Close source panel"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Relevance legend */}
      <div className="flex items-center gap-2 px-4 py-2 bg-surface-900/30 border-b border-white/5">
        <div className="flex gap-1 items-center">
          <div className="w-8 h-1.5 rounded-full bg-gradient-to-r from-brand-600 to-brand-400" />
          <span className="text-xs text-gray-500">High</span>
        </div>
        <div className="flex gap-1 items-center">
          <div className="w-8 h-1.5 rounded-full bg-gradient-to-r from-gray-600 to-gray-500" />
          <span className="text-xs text-gray-500">Low</span>
        </div>
        <span className="text-xs text-gray-600 ml-auto">Semantic relevance</span>
      </div>

      {/* Cards */}
      <div className="flex-1 overflow-y-auto px-3 py-3 space-y-3">
        {sources.map((src, i) => (
          <SourceCard key={i} source={src} index={i} />
        ))}
      </div>
    </aside>
  )
}
