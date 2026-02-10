/** 
props

items (favorites)

onClickItem (상세로 이동 or 모달)

onRemove, onAddToCollection 같은 액션(선택)

내부는:

SectionHeader

EmptyState or FavoritesGrid
*/

import React from 'react'
import EmptyState from './EmptyState.jsx'

/**
 * FavoritesSection
 * props:
 * - favorites: [{ itemKey, imageUrl, title, ... }]
 * - onClickItem: (item) => void
 */
const FavoritesSection = ({ favorites = [], onClickItem }) => {
  return (
    <section className="mt-8">
      <div className="flex items-end justify-between">
        <h3 className="text-lg font-semibold">
          좋아요{' '}
          <span className="text-sm text-muted-foreground">
            ({favorites.length})
          </span>
        </h3>
      </div>

      {favorites.length === 0 ? (
        <EmptyState
          title="아직 좋아요가 없어요"
          description="마음에 드는 코디를 ❤️로 저장해두면 여기서 모아볼 수 있어요."
        />
      ) : (
        <div className="mt-3 grid grid-cols-2 md:grid-cols-4 gap-4">
          {favorites.map((it) => (
            <button
              key={it.itemKey}
              type="button"
              onClick={() => onClickItem?.(it)}
              className="group block overflow-hidden rounded-xl"
              title={it.title}
            >
              <img
                src={it.imageUrl}
                alt={it.title}
                loading="lazy"
                className="w-full h-56 object-cover rounded-xl transition-transform duration-200 group-hover:scale-[1.02]"
              />
            </button>
          ))}
        </div>
      )}
    </section>
  )
}

export default FavoritesSection
