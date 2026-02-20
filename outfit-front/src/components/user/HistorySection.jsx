// src/components/user/HistorySection.jsx
import React from 'react'
import EmptyState from './EmptyState.jsx'

/*
HistorySection
- 추천 요청 단위 히스토리를 보여주는 섹션
- 각 항목은 input(category/gender/텍스트) + items(추천 결과) 요약으로 구성
- 클릭 시 해당 요청의 결과를 모달로 열기 위한 콜백(onClickHistory)을 외부에서 주입
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
              {/* 메타 정보: 시간 + 카테고리/성별 */}
              <div className="text-sm text-muted-foreground">
                {new Date(h.createdAt ?? Date.now()).toLocaleString()}
                {' · '}
                {h.input?.category} / {h.input?.gender}
              </div>

              {/* 결과 미리보기: 최대 4장만 노출 */}
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
