/** 
HistorySection + HistoryCard

HistoryCard는 “요청 단위 카드”로 고정하는 게 좋아.

meta 줄: 날짜 / category / gender / textQuery

preview grid: 4장

버튼: “상세 보기”, “다시 추천(재요청)” (가능하면)

그리고 key는 지금처럼 fallback 주는 건 임시방편이야.

가능하면 history 항목에 항상 고유 id (ex: historyId)를 만들어두는 게 안정적.
*/

import React from 'react'
import EmptyState from './EmptyState.jsx'

/**
 * HistorySection
 * props:
 * - history: [{ turnId, requestId, createdAt, input:{category,gender}, items:[...] }]
 * - onClickHistory: (historyItem) => void
 */
const HistorySection = ({ history = [], onClickHistory }) => {
  return (
    <section className="mt-10">
      <div className="flex items-end justify-between">
        <h3 className="text-lg font-semibold">
          히스토리(요청 단위){' '}
          <span className="text-sm text-muted-foreground">
            ({history.length})
          </span>
        </h3>
      </div>

      {history.length === 0 ? (
        <EmptyState
          title="아직 히스토리가 없어요"
          description="첫 추천을 받으면 요청 단위로 기록이 쌓여요."
        />
      ) : (
        <div className="mt-3 space-y-4">
          {history.map((h) => (
            <button
              key={`${h.turnId ?? 'noTurn'}:${h.requestId ?? 'noReq'}`}
              type="button"
              onClick={() => onClickHistory?.(h)}
              className="w-full text-left rounded-xl border p-4 hover:bg-accent/40 transition-colors"
            >
              <div className="text-sm text-muted-foreground">
                {new Date(h.createdAt ?? Date.now()).toLocaleString()}
                {' · '}
                {h.input?.category} / {h.input?.gender}
              </div>

              <div className="mt-3 grid grid-cols-4 gap-3">
                {(h.items ?? []).slice(0, 4).map((it) => (
                  <img
                    key={it.itemKey}
                    src={it.imageUrl}
                    alt={it.title}
                    loading="lazy"
                    className="w-full h-56 object-cover rounded-lg"
                  />
                ))}
              </div>
            </button>
          ))}
        </div>
      )}
    </section>
  )
}

export default HistorySection
