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

function renderFormattedText(text) {
  const lines = String(text ?? "").split("\n");

  return (
    <div className="space-y-2">
      {lines.map((line, i) => {
        const trimmed = line.trim();

        if (!trimmed) {
          return <div key={i} className="h-2" />;
        }

        // ### h3
        if (trimmed.startsWith("### ")) {
          return (
            <h3 key={i} className="text-base font-semibold leading-snug">
              {trimmed.replace("### ", "")}
            </h3>
          );
        }

        // ## h2
        if (trimmed.startsWith("## ")) {
          return (
            <h2 key={i} className="text-lg font-semibold leading-snug">
              {trimmed.replace("## ", "")}
            </h2>
          );
        }

        // 일반 문단
        return (
          <p
            key={i}
            className="text-base leading-relaxed whitespace-pre-wrap break-words"
          >
            {trimmed}
          </p>
        );
      })}
    </div>
  );
}

const AIMessage = ({
  content = '',
  role = 'assistant',
  variant = 'default',
}) => {
  const text = String(content ?? '').trim()

<<<<<<< Updated upstream
  // 로딩 플레이스홀더 감지: '…'
  const isTyping = role === 'assistant' && variant !== 'error' && text === '…'

  // 로딩이면 text가 비어도 렌더
  if (!text && !isTyping) return null
=======
  const isTyping = role === "assistant" && variant !== "error" && text === "…";

  if (!text && !isTyping) return null;
>>>>>>> Stashed changes

  const isUser = role === 'user'
  const isError = variant === 'error'

  const align = isUser ? 'ml-auto mr-4' : 'mr-auto ml-4'

  const tone = isError
    ? 'bg-red-50 text-red-700 border border-red-200'
    : isUser
<<<<<<< Updated upstream
      ? 'bg-card/80 text-foreground'
      : 'bg-muted/60 text-foreground'
=======
      ? "bg-muted text-foreground"
      : "bg-muted/60 text-foreground";
>>>>>>> Stashed changes

  return (
    <div
      className={`${align} text-base mt-3 w-fit max-w-[420px] rounded-2xl px-4 py-3 shadow break-words ${tone}`}
    >
      {isTyping ? (
        <TypingDots />
      ) : role === "assistant" ? (
        renderFormattedText(text)
      ) : (
        <div className="whitespace-pre-wrap leading-relaxed">{text}</div>
      )}
    </div>
  )
}

export default AIMessage
