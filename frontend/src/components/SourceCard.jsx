import { useState } from 'react'

export default function SourceCard({ source, index }) {
  const [expanded, setExpanded] = useState(false)
  const pct    = Math.round(source.relevance_score * 100)
  const pages  = source.page_numbers

  const pageLabel = pages.length === 1
    ? `Page ${pages[0]}`
    : `Pages ${pages[0]}–${pages[pages.length - 1]}`

  // Colour the bar based on relevance
  const barColour =
    pct >= 80 ? 'from-brand-600 to-brand-400' :
    pct >= 60 ? 'from-yellow-600 to-yellow-400' :
                'from-gray-600 to-gray-500'

  return (
    <div className="glass p-4 flex flex-col gap-3 transition-all duration-200
                    hover:border-brand-500/20 hover:bg-surface-700/40 animate-fade-in">

      {/* Header row */}
      <div className="flex items-center justify-between gap-2">
        <span className="source-badge shrink-0">
          <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round"
              d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
          </svg>
          {pageLabel}
        </span>

        <div className="flex items-center gap-2 ml-auto">
          <span className="text-xs font-mono text-gray-500">{pct}%</span>
          <button
            onClick={() => setExpanded(v => !v)}
            className="text-gray-600 hover:text-gray-300 transition-colors"
            aria-label={expanded ? 'Collapse excerpt' : 'Expand excerpt'}
          >
            <svg
              className={`w-4 h-4 transition-transform duration-200 ${expanded ? 'rotate-180' : ''}`}
              fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
            </svg>
          </button>
        </div>
      </div>

      {/* Relevance bar */}
      <div className="h-1 bg-surface-600 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full bg-gradient-to-r ${barColour} transition-all duration-700`}
          style={{ width: `${pct}%` }}
        />
      </div>

      {/* Excerpt text */}
      <p className={`text-xs text-gray-400 leading-relaxed transition-all duration-200
                     ${expanded ? '' : 'line-clamp-3'}`}>
        {source.chunk_text}
      </p>

      {/* Expand hint */}
      {!expanded && source.chunk_text.length > 200 && (
        <button
          onClick={() => setExpanded(true)}
          className="text-xs text-brand-400 hover:text-brand-300 transition-colors self-start"
        >
          Show more…
        </button>
      )}
    </div>
  )
}
