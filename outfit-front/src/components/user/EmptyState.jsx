// src/components/user/EmptyState.jsx
import React from 'react'

/*
EmptyState
- 즐겨찾기/히스토리 섹션 등에서 목록이 비어있을 때 재사용하는 UI
- 버튼 액션(onAction)은 선택적으로 제공(예: 추천 받으러 가기)
*/
const EmptyState = ({ title, description, actionText, onAction }) => {
  return (
    <div className="mt-3 rounded-xl border border-dashed p-8 text-center">
      <p className="text-base font-semibold">{title}</p>

      {description && (
        <p className="mt-2 text-sm text-muted-foreground">{description}</p>
      )}

      {actionText && onAction && (
        <button
          type="button"
          onClick={onAction}
          className="mt-4 inline-flex items-center justify-center rounded-lg border px-4 py-2 text-sm font-medium hover:bg-accent"
        >
          {actionText}
        </button>
      )}
    </div>
  )
}

export default EmptyState
