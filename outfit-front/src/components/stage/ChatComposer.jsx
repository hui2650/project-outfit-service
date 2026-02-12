import React from 'react'

// ChatComposer.jsx 수정
export default function ChatComposer({ disabled = false, onSend }) {
  const [text, setText] = React.useState('')

  const submit = () => {
    const v = text.trim()
    if (!v || disabled) return
    onSend?.(v)
    setText('')
  }

  return (
    <div className="absoulte w-full pb-6 pt-4 bg-gradient-to-t from-background/60 via-background/20 to-transparent pointer-events-none">
      <div className="pointer-events-auto w-full px-4">
        <div className="mx-auto w-full max-w-3xl rounded-2xl border border-border bg-card shadow-2xl px-3 py-2">
          <div className="flex items-center gap-2">
            <input
              value={text}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  submit()
                }
              }}
              disabled={disabled}
              placeholder={
                disabled
                  ? '결과가 있을 때 질문 가능합니다.'
                  : '질문을 입력하세요...'
              }
              className="flex-1 bg-transparent outline-none text-sm pl-2 placeholder:text-muted-foreground disabled:opacity-60"
            />
            <button
              type="button"
              onClick={submit}
              disabled={disabled || !text.trim()}
              className="h-9 px-4 rounded-xl bg-primary text-primary-foreground text-sm font-bold hover:opacity-90 transition-all active:scale-95 disabled:opacity-30"
            >
              전송
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
