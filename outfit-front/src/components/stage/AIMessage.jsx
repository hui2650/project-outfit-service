import React from 'react'

const TypingDots = () => {
  return (
    <div className="flex items-center gap-1">
      <span className="w-2 h-2 rounded-full bg-foreground/60 animate-bounce [animation-delay:-0.3s]" />
      <span className="w-2 h-2 rounded-full bg-foreground/60 animate-bounce [animation-delay:-0.15s]" />
      <span className="w-2 h-2 rounded-full bg-foreground/60 animate-bounce" />
    </div>
  )
}

const AIMessage = ({
  content = '',
  role = 'assistant',
  variant = 'default',
}) => {
  const text = String(content ?? '').trim()

  // 로딩 플레이스홀더 감지: '…'
  const isTyping = role === 'assistant' && variant !== 'error' && text === '…'

  // 로딩이면 text가 비어도 렌더
  if (!text && !isTyping) return null

  const isUser = role === 'user'
  const isError = variant === 'error'

  const align = isUser ? 'ml-auto mr-4' : 'mr-auto ml-4'

  const tone = isError
    ? 'bg-red-50 text-red-700 border border-red-200'
    : isUser
      ? 'bg-card/80 text-foreground'
      : 'bg-muted/60 text-foreground'

  return (
    <div
      className={`${align} mt-3 w-fit max-w-[420px] rounded-2xl px-4 py-3 shadow whitespace-pre-wrap break-words leading-relaxed ${tone}`}
    >
      {isTyping ? <TypingDots /> : text}
    </div>
  )
}

export default AIMessage
