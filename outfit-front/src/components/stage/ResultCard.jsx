// src/components/stage/ResultCard.jsx
import React from "react";
import LikeButton from "../common/LikeButton";

const ResultCard = ({ item, onClick }) => {
  return (
    <div
      onClick={onClick}
      className="relative h-[360px] rounded-2xl overflow-hidden bg-card border border-border cursor-pointer group"
    >
      <img
        src={item.imageUrl}
        alt={item.title || "outfit"}
        className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
      />

      {/* 좋아요 버튼 */}
      <LikeButton item={item} variant="card" />

      {/* 하단 정보 */}
      <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/60 to-transparent p-4 text-white">
        <p className="text-sm font-medium line-clamp-2">{item.title}</p>
      </div>
    </div>
  );
};

export default ResultCard;
