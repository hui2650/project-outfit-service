import React from "react";

const ResultCard = ({ item, onClick }) => {
  return (
    <button
      type="button"
      onClick={onClick}
      className="w-full h-[360px] rounded-2xl overflow-hidden shadow bg-white group"
    >
      <img
        src={item.imageUrl}
        alt={item.title}
        className="w-full h-full object-cover group-hover:scale-[1.02] transition-transform"
        loading="lazy"
      />
    </button>
  );
};

export default ResultCard;
