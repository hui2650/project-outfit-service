import React from 'react'

const AIMessage = ({
  content = '',
  role = 'assistant',
  variant = 'default',
}) => {
  const text = String(content ?? '').trim()
  if (!text) return null

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
      {text}
    </div>
  )
}

export default AIMessage
