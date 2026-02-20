// src/components/stage/ChatPreview.jsx
import React from 'react'

/**
 *  ChatPreview (유저가 보낸 "입력 미리보기" 버블)
 * - 입력은 "이미지 + 텍스트쿼리" 복합이라
 *   유저 메시지를 일반 텍스트 버블로만 보여주면 정보가 날아감
 * - 그래서 input 메시지 타입은:
 *   이미지(업로드한 아이템) + textQuery(원하는 스타일/조건) 형태로 렌더
 */

const ChatPreview = ({ previewUrl, textQuery }) => {
  // 이미지도 있고, 텍스트도 있을 때만 텍스트 영역 노출
  const hasSomething = previewUrl && textQuery && textQuery.trim().length > 0

  return (
    // user bubble 느낌: 오른쪽 정렬(ml-auto) + muted background
    <div className="ml-auto md:mr-4 mt-6 mb-8 w-fit max-w-[280px] md:max-w-[320px] bg-muted rounded-2xl shadow p-3 md:p-4">
      {previewUrl && (
        <img
          src={previewUrl}
          alt="sent"
          // object-contain: 아이템 사진 잘리지 않게 (코디 서비스라 중요)
          className="w-full h-32 md:h-36 object-contain rounded-xl bg-card"
        />
      )}

      {hasSomething && (
        <p className="mt-3 text-md md:text-base text-secondary-foreground break-words">
          {textQuery?.trim() ? textQuery : ''}
        </p>
      )}
    </div>
  )
}

export default ChatPreview
