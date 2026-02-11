import React from 'react'
import Turn from './Turn'
import EmptyResult from './EmptyResult'
import ChatComposer from './ChatComposer'

const ResultStage = ({ chatLogs, onSelectItem, onSendChat, chatDisabled }) => {
  const bottomRef = React.useRef(null)

  const isOnlyLoading =
    chatLogs.length === 1 && chatLogs[0].status === 'loading'

  const hasLoading = chatLogs?.some((turn) => turn.status === 'loading')

  React.useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [chatLogs])

  // 비어있을 때는 EmptyResult에서 가운데 정렬 처리하는 게 제일 깔끔
  if (!chatLogs || chatLogs.length === 0) {
    return (
      <div className="h-full flex flex-col">
        <div className="flex-1">
          <EmptyResult />
        </div>
        <ChatComposer disabled={true} onSend={onSendChat} />
      </div>
    )
  }

  return (
    <div className="flex flex-col relative overflow-hidden">
      {/* ✅ 스크롤 영역: flex-1로 남는 공간 다 차지함 */}
      <div
        className={`flex-1 px-4 ${
          isOnlyLoading
            ? 'overflow-hidden'
            : `overflow-y-auto [scrollbar-width:none] [-ms-overflow-style:none] ${
                hasLoading ? '' : 'pb-[140px]'
              }`
        }`}
        style={{ scrollbarGutter: 'stable' }}
      >
        <div className="w-full max-w-none lg:max-w-7xl mx-auto ">
          {chatLogs.map((turn) => (
            <Turn key={turn.id} turn={turn} onSelectItem={onSelectItem} />
          ))}
          <div ref={bottomRef} />
        </div>

        {/* 입력창이 가리지 않게 충분한 하단 여백 부여 로딩중일땐 보이지 않게 하기*/}
        {!hasLoading && <div className="h-24" />}
      </div>

      {/* 고정 위치: sticky 대신 absolute/fixed 느낌으로 하단에 배치 */}
      <div className="absolute bottom-0 left-0 w-full z-10">
        <ChatComposer disabled={chatDisabled} onSend={onSendChat} />
      </div>
    </div>
  )
}

export default ResultStage
