// src/components/stage/ResultCard.jsx
import React from 'react'
import LikeButton from '../common/LikeButton'

/**
 * ResultCard (결과 카드 1개)
 * - 추천된 코디 이미지 1장을 카드로 보여줌
 * - 클릭하면 ResultModal로 확대/상세보기 (ResultCarousel에서 관리)
 * - LikeButton으로 저장/즐겨찾기 기능(appDataStore) 연동
 */

const ResultCard = ({ item, onClick }) => {
  return (
    <div
      onClick={onClick}
      // 카드 레이아웃: 이미지 꽉 채우고 hover 시 확대
      className="relative h-[360px] rounded-2xl overflow-hidden bg-card border border-border cursor-pointer group"
    >
      <img
        src={item.imageUrl}
        alt={item.title || 'outfit'}
        className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
      />

      {/* 좋아요 버튼 */}
      <LikeButton item={item} variant="card" />

      {/* 하단 정보 */}
      <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/60 to-transparent p-4 text-white">
        <p className="text-sm font-medium line-clamp-2">{item.title}</p>
      </div>
    </div>
  )
}

export default ResultCard
