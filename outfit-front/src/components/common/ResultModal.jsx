import React from 'react'
import { useAppData } from '../../store/appDataStore.jsx'
import LikeButton from './LikeButton.jsx'

const ResultModal = ({ items, index, onClose, onChangeIndex }) => {
  const item = items?.[index] // ✅ 먼저 잡기 (방어)

  const { isLiked, toggleLike } = useAppData()
  const liked = item ? isLiked(item) : false // ✅ item 없으면 false

  // Esc로 닫기
  React.useEffect(() => {
    const onKeyDown = (e) => {
      if (e.key === 'Escape') onClose()
      if (e.key === 'ArrowLeft') prev()
      if (e.key === 'ArrowRight') next()
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [index, items, onClose])

  // 모달 열릴 때만 바디 스크롤 잠그기
  React.useEffect(() => {
    // items/index가 없어서 item이 없으면 잠그지 않음
    if (!item) return

    const prevOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    return () => {
      document.body.style.overflow = prevOverflow
    }
  }, [item])

  const prev = () => {
    if (index > 0) onChangeIndex(index - 1)
  }

  const next = () => {
    if (index < (items?.length ?? 0) - 1) onChangeIndex(index + 1)
  }

  // ✅ item이 없으면 렌더 자체를 막아버리기 (안전)
  if (!item) return null

  return (
    <div className="fixed inset-0 z-[1000]">
      {/* 어두운 배경 (클릭하면 닫힘) */}
      <div
        className="absolute inset-0 bg-foreground/60"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* 중앙 컨텐츠 */}
      <div className="relative h-full w-full flex items-center justify-center p-6">
        <div className="relative w-full max-w-5xl">
          {/* 닫기 버튼 */}
          <button
            type="button"
            onClick={onClose}
            className="absolute -top-12 right-0 text-card/90 hover:text-card text-3xl"
            aria-label="close"
          >
            ×
          </button>

          {/* 좌우 버튼 */}
          <button
            type="button"
            onClick={prev}
            disabled={index === 0}
            className="
            absolute left-4 top-1/2 -translate-y-1/2
            h-8 w-8
            rounded-full
            bg-black/40
            backdrop-blur-sm
            text-white text-lg
            flex items-center justify-center
            transition
            hover:bg-black/60
            disabled:opacity-30
            z-10
          "
          >
            ←
          </button>

          <button
            type="button"
            onClick={next}
            disabled={index === items.length - 1}
            className="
            absolute right-4 top-1/2 -translate-y-1/2
            h-8 w-8
            rounded-full
            bg-black/40
            backdrop-blur-sm
            text-white text-lg
            flex items-center justify-center
            transition
            hover:bg-black/60
            disabled:opacity-30
            z-10
          "
          >
            →
          </button>

          {/* 카드: 이미지 + 설명 */}
          <div className="bg-white rounded-2xl overflow-hidden shadow-xl grid grid-cols-1 md:grid-cols-[1fr_320px]">
            {/* 이미지 크게 */}
            <div className="relative bg-black">
              <img
                src={item.imageUrl}
                alt={item.title}
                className="w-full h-[70vh] object-contain bg-black"
              />

              {/* 좋아요 버튼 */}
              <LikeButton item={item} variant="modal" />
            </div>

            {/* 설명 박스 */}
            <div className="p-5 border-t md:border-t-0 md:border-l">
              <div className="text-xs text-gray-500 mb-2">
                Source: {item.source}
              </div>

              <div className="text-lg font-bold text-gray-900">
                {item.title || 'Untitled'}
              </div>

              <div className="mt-3 text-sm text-gray-600 leading-relaxed">
                이 코디는 업로드한 아이템과 유사한 스타일로 추천된 이미지입니다.
              </div>

              <div className="mt-5 flex gap-2">
                <button
                  type="button"
                  className="px-4 py-2 rounded-lg bg-violet-600 text-white font-semibold"
                  onClick={onClose}
                >
                  확인
                </button>
              </div>
            </div>
          </div>

          <div className="mt-3 text-center text-xs text-white/70">
            배경 클릭 또는 ESC로 닫기 · ← → 로 넘기기
          </div>
        </div>
      </div>
    </div>
  )
}

export default ResultModal
