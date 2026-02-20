import React from 'react'
import ResultCarousel from './ResultCarousel'
import OutfitLoadingMark from '../common/OutfitLoadingMark'
import AIMessage from './AIMessage'
import ChatPreview from './ChatPreview'

/**
 * Turn (한 턴=한 번의 유저 입력 + 그에 대한 응답 묶음)
 * - 프로젝트의 구조:
 *   1) input: 유저 업로드 이미지 + 텍스트 조건
 *   2) text: AI 설명/추천 이유
 *   3) carousel: 추천 이미지 목록
 *   4) error: 실패 메시지
 *
 * - turn.status === "loading"이면 "추천 생성 중" 전체 로딩 화면을 보여줌
 *   (중복 요청 방지/UX를 위해 중앙 로딩)
 */

const Turn = ({ turn, onSelectItem }) => {
  /* ===============================
     로딩 전용 Turn
     =============================== */
  if (turn.status === 'loading') {
    return (
      <div className="w-full h-[calc(100vh-54px)] flex-1 flex items-center justify-center">
        {/* 추천 생성중 로딩 표시 (FastAPI + 외부 API 지연 대비) */}
        <OutfitLoadingMark />
      </div>
    )
  }

  /* ===============================
     일반 Turn (채팅 렌더)
     =============================== */
  return (
    <div className="w-full">
      {turn.messages.map((msg) => {
        // 유저 입력 미리보기: 이미지+텍스트
        if (msg.type === 'input') {
          return (
            <ChatPreview
              key={msg.id}
              previewUrl={msg.previewUrl}
              textQuery={msg.text}
            />
          )
        }

        // 텍스트 메시지: AIMessage로 렌더(assistant/user 모두 가능)
        if (msg.type === 'text') {
          return (
            <AIMessage key={msg.id} content={msg.content} role={msg.role} />
          )
        }

        // 결과 캐러셀: 추천된 코디 이미지들
        if (msg.type === 'carousel') {
          return (
            <ResultCarousel key={msg.id} items={msg.items} loading={false} />
          )
        }

        // 에러 메세지: AIMessage error variant 사용
        if (msg.type === 'error') {
          return (
            <AIMessage key={msg.id} content={msg.message} variant="error" />
          )
        }

        return null
      })}
    </div>
  )
}

export default Turn
