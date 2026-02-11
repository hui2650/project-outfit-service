/**
Empty 처리

if (!favorites?.length) ...
if (!history?.length) ...

이미지에 loading="lazy" 추가

new Date(...).toLocaleString()는 렌더마다 돌면 비효율이라
HistoryCard에서 useMemo로 포맷팅(혹은 유틸 함수)

favorites/history가 undefined일 수 있으니 안전하게:

{(favorites ?? []).map(...) }

히스토리 “요청 단위”는 보통 최신 10개만 먼저 보여주고 “더보기”가 UX 좋음

섹션 title 옆에 “개수 배지”

좋아요 23개 / 히스토리 51개
 */

import React from 'react'

/**
 * EmptyState
 * - title: 메인 문구
 * - description: 보조 문구(선택)
 * - actionText: 버튼 텍스트(선택)
 * - onAction: 버튼 클릭 핸들러(선택)
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
