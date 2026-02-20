import React from 'react'

/**
 *  AIMessage
 * - 채팅 버블(assistant / user / error)을 렌더링하는 컴포넌트
 * - FastAPI/LLM 응답을 텍스트로 보여주는 UI
 * - "…" 를 로딩 상태(타이핑)로 취급해 점점점 애니메이션을 보여줌
 */

// 로딩 ui : LLM 응답 대기 중
const TypingDots = () => {
  return (
    <div className="flex items-center gap-1">
      {/* animation-delay를 음수로 줘서 시작 타이밍을 어긋나게(리듬감) */}
      <span className="w-2 h-2 rounded-full bg-foreground/60 animate-bounce [animation-delay:-0.3s]" />
      <span className="w-2 h-2 rounded-full bg-foreground/60 animate-bounce [animation-delay:-0.15s]" />
      <span className="w-2 h-2 rounded-full bg-foreground/60 animate-bounce" />
    </div>
  )
}
/**
 *  renderFormattedText
 * - LLM 응답을 최소 마크다운(##, ###)만 지원해서 예쁘게 렌더
 * - 완전한 markdown 라이브러리 대신 "안전/간단/예측가능"한 렌더링을 선택
 * - 프로젝트에서 LLM이:
 *   "## 코디 포인트", "### 색 조합", "### 신발 추천" 이런 식으로 내면 UX 좋아짐
 */
function renderFormattedText(text) {
  const lines = String(text ?? '').split('\n')

  return (
    <div className="space-y-2">
      {lines.map((line, i) => {
        const trimmed = line.trim()

        if (!trimmed) return <div key={i} className="h-2" />

        if (trimmed.startsWith('### ')) {
          return (
            <h3
              key={i}
              className="text-md md:text-base font-semibold leading-snug"
            >
              {trimmed.replace('### ', '')}
            </h3>
          )
        }

        if (trimmed.startsWith('## ')) {
          return (
            <h2
              key={i}
              className="text-base md:text-lg font-semibold leading-snug"
            >
              {trimmed.replace('## ', '')}
            </h2>
          )
        }

        return (
          <p
            key={i}
            className="text-md md:text-base leading-relaxed whitespace-pre-wrap break-words"
          >
            {trimmed}
          </p>
        )
      })}
    </div>
  )
}

const AIMessage = ({
  content = '',
  role = 'assistant',
  variant = 'default',
}) => {
  // content가 null/undefined여도 안전하게 문자열 처리
  const text = String(content ?? '').trim()

  // "…" 를 타이핑 로딩으로 취급 (LLM pending 표현 규칙)
  const isTyping = role === 'assistant' && variant !== 'error' && text === '…'

  // 아무 내용도 없고, typing도 아니면 렌더할 필요 없음
  if (!text && !isTyping) return null

  const isUser = role === 'user'
  const isError = variant === 'error'

  // 말풍선 정렬: user는 오른쪽, assistant는 왼쪽
  const align = isUser ? 'ml-auto md:mr-4' : 'mr-auto md:ml-4'

  // 말풍선 톤: error / user / assistant
  const tone = isError
    ? 'bg-red-50 text-red-700 border border-red-200'
    : isUser
      ? 'bg-muted text-foreground'
      : 'bg-muted/60 text-foreground'

  return (
    <div
      className={[
        align,
        // 말풍선 공통 스타일
        'mt-3 w-fit rounded-2xl shadow break-words',
        'px-3 py-2 md:px-4 md:py-3',
        'text-md md:text-base',
        // 길이 제한: 모바일/데스크톱 최적(너무 길게 퍼지지 않게)
        'max-w-[300px] md:max-w-[420px]',
        tone,
      ].join(' ')}
    >
      {/* 상태별 렌더링 */}
      {isTyping ? (
        <TypingDots />
      ) : role === 'assistant' ? (
        renderFormattedText(text)
      ) : (
        <div className="whitespace-pre-wrap leading-relaxed">{text}</div>
      )}
    </div>
  )
}

export default AIMessage
