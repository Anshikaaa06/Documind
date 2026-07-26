// Renders a subset of markdown: **bold** and [Source: Page X] citation badges
function renderContent(text) {
  if (!text) return null

  // Split on **bold** and [Source: ...] patterns
  const parts = text.split(/(\*\*[^*]+\*\*|\[Source:[^\]]+\])/g)

  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={i} className="font-semibold text-gray-100">{part.slice(2, -2)}</strong>
    }
    if (part.startsWith('[Source:')) {
      return (
        <span key={i} className="source-badge mx-0.5 align-middle">
          {part.slice(1, -1)}
        </span>
      )
    }
    // Preserve line breaks
    return part.split('\n').map((line, j, arr) => (
      <span key={`${i}-${j}`}>
        {line}
        {j < arr.length - 1 && <br />}
      </span>
    ))
  })
}

export default function ChatMessage({ message }) {
  const isUser = message.role === 'user'

  return (
    <div className={`flex gap-3 animate-slide-up ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>

      {/* Avatar */}
      <div className={`
        shrink-0 w-8 h-8 rounded-xl flex items-center justify-center text-xs font-bold select-none
        ${isUser
          ? 'bg-gradient-to-br from-brand-600 to-brand-400 text-white shadow-md shadow-brand-900/40'
          : 'bg-surface-600 text-gray-400'}
      `}>
        {isUser
          ? <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round"
                d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
            </svg>
          : <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round"
                d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
            </svg>
        }
      </div>

      {/* Bubble */}
      <div className={`
        max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed
        ${isUser
          ? 'bg-brand-600/25 text-gray-100 rounded-tr-sm border border-brand-500/20'
          : 'glass text-gray-200 rounded-tl-sm'}
      `}>
        {message.loading ? (
          <div className="dot-pulse flex items-center gap-1 py-1">
            <span /><span /><span />
          </div>
        ) : (
          <p>{renderContent(message.content)}</p>
        )}

        {/* Footer: model + token usage */}
        {!message.loading && message.model && (
          <div className="mt-2.5 pt-2 border-t border-white/5 flex items-center gap-1.5 text-xs text-gray-600 flex-wrap">
            <svg className="w-3 h-3 text-brand-500/60" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round"
                d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
            </svg>
            <span className="text-gray-600">{message.model}</span>
            {message.usage && (
              <>
                <span className="text-gray-700">·</span>
                <span>{message.usage.input} in</span>
                <span className="text-gray-700">/</span>
                <span>{message.usage.output} out tokens</span>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
