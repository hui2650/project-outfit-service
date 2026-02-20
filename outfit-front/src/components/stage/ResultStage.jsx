// src/components/stage/ResultStage.jsx
import React from 'react'
import Turn from './Turn'
import EmptyResult from './EmptyResult'
import ChatComposer from './ChatComposer'
import { useChatPage } from '../../pages/chat/ChatPageContext'

/**
 *  ResultStage (왼쪽 메인 영역)
 * - 채팅 로그(추천/채팅 턴)를 전체 렌더링하는 컨테이너
 * - "결과가 있어야 질문 가능" 규칙을 UI로 강제(ChatComposer disabled)
 *
 * 핵심 UX:
 * - safeLogs: chatLogs가 꼬여도 UI 죽지 않게 방어
 * - bottomRef: 새 메시지 올 때 자동 스크롤(맨 아래로)
 * - emptyReloadKey: 새로고침/세션 전환 시 EmptyResult 타이핑 효과 재시작용
 */

const ResultStage = ({ chatLogs, onSelectItem, onSendChat, chatDisabled }) => {
  const bottomRef = React.useRef(null)
  const safeLogs = Array.isArray(chatLogs) ? chatLogs : []

  // chatLogs가 null/undefined여도 map 터지지 않게
  const { emptyReloadKey } = useChatPage()

  // "로딩 turn만 1개 있을 때" 스크롤을 막아서 중앙 로딩이 깔끔하게 보이게
  const isOnlyLoading =
    safeLogs.length === 1 && safeLogs[0].status === 'loading'

  // 로그가 바뀌면 맨 아래로 스크롤 (새로운 응답/추천이 내려오므로)
  React.useEffect(() => {
    bottomRef.current?.scrollIntoView({
      behavior: 'smooth',
      block: 'end',
      inline: 'nearest',
    })
  }, [safeLogs])

  // 처음 진입: EmptyResult + 입력창(비활성)
  if (safeLogs.length === 0) {
    return (
      <div className="flex-1 flex flex-col">
        <div className="flex-1 flex items-center justify-center">
          {/* key를 바꿔 타이핑 애니메이션을 강제로 다시 시작 */}
          <EmptyResult key={emptyReloadKey} />
        </div>

        {/* 결과 없을 땐 질문 불가 */}
        <ChatComposer disabled={true} onSend={onSendChat} />
      </div>
    )
  }

  return (
    <div className="flex-1 flex flex-col min-h-0">
      {/* 스크롤 영역 
      - 이 영역에서 채팅/추천 카드가 길어지면 스크롤
          - 로딩만 있을 땐 overflow 숨김(중앙 로딩이 흔들리지 않게) */}
      <div
        className={[
          'h-full',
          'px-4 sm:px-6 lg:px-8', // 모바일 표준
          isOnlyLoading
            ? 'overflow-hidden'
            : 'overflow-y-auto [scrollbar-width:none] [-ms-overflow-style:none]',
        ].join(' ')}
        style={{ scrollbarGutter: 'stable' }}
      >
        <div className="w-full max-w-none lg:max-w-7xl mx-auto">
          {/* Turn 단위 렌더: 각 turn은 input/text/carousel/error를 포함 */}
          {safeLogs.map((turn) => (
            <Turn key={turn.id} turn={turn} onSelectItem={onSelectItem} />
          ))}
          {/* 아래 여백 + 자동 스크롤 기준점 */}
          <div className="h-24" ref={bottomRef} />
        </div>

        {/* follow-up 질문 입력창 */}
        <ChatComposer disabled={chatDisabled} onSend={onSendChat} />
      </div>
    </div>
  )
}

export default ResultStage
