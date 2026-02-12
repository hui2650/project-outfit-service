import React from 'react'

const ChatPreview = ({ previewUrl, textQuery }) => {
  const hasSomething = previewUrl && textQuery && textQuery.trim().length > 0

  return (
    <div className="ml-auto mr-4 mt-6 mb-8 w-fit max-w-[320px] bg-card/80 rounded-2xl shadow p-4">
      <div className="text-xs text-gray-500"></div>

      {previewUrl && (
        <img
          src={previewUrl}
          alt="sent"
          className="w-full h-36 object-contain rounded-xl bg-card"
          onError={(e) => {
            // blob URL이 만료/해제된 경우 콘솔 ERR_FILE_NOT_FOUND 방지: 이미지 숨김 처리
            e.currentTarget.style.display = 'none'
          }}
        />
      )}

      {/* 텍스트 있는 경우에만 */}
      {hasSomething && (
        <p className="mt-3 text-secondary-foreground">
          {textQuery?.trim() ? textQuery : ''}
        </p>
      )}
    </div>
  )
}

export default ChatPreview
