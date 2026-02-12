import React from 'react'
import Turn from './Turn'
import EmptyResult from './EmptyResult'
import ChatComposer from './ChatComposer'

const ResultStage = ({
  chatLogs,
  onSelectItem,
  onSendChat,
  chatDisabled,
  onNewChat,
}) => {
  const bottomRef = React.useRef(null)
  const safeLogs = Array.isArray(chatLogs) ? chatLogs : []

  const isOnlyLoading =
    safeLogs.length === 1 && safeLogs[0].status === 'loading'

  const hasLoading = safeLogs.some((turn) => turn.status === 'loading')

  // 기존 정책 유지: 로그 변경 시 맨 아래로
  React.useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [safeLogs])

  if (safeLogs.length === 0) {
    return (
      <div className="flex-1 flex flex-col">
        <div className="flex-1 flex items-center justify-center">
          <EmptyResult />
        </div>

        <ChatComposer disabled={true} onSend={onSendChat} />
      </div>
    )
  }

  return (
    <div className="flex-1 flex flex-col min-h-0">
      {/* 스크롤 영역 */}
      <div
        className={`h-full px-4 ${
          isOnlyLoading
            ? 'overflow-hidden'
            : 'overflow-y-auto [scrollbar-width:none] [-ms-overflow-style:none]'
        }`}
        style={{ scrollbarGutter: 'stable' }}
      >
        <div className="w-full max-w-none lg:max-w-7xl mx-auto">
          {safeLogs.map((turn) => (
            <Turn key={turn.id} turn={turn} onSelectItem={onSelectItem} />
          ))}
          <div ref={bottomRef} />
        </div>
      </div>

      <ChatComposer disabled={chatDisabled} onSend={onSendChat} />
    </div>
  )
}

export default ResultStage
