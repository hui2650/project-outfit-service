import React from "react";
import { useAppData } from "../../store/appDataStore.jsx";

const PRESET = {
  card: {
    btn: "h-8 w-8",
    icon: "text-xl",
    pos: "top-2 right-2",
    bg: "bg-card/75",
  },
  modal: {
    btn: "h-10 w-10",
    icon: "text-2xl",
    pos: "top-3 right-3",
    bg: "bg-card/75",
  },
};

export default function LikeButton({
  item,
  variant = "card", // "card" | "modal"
  className = "",
  stopPropagation = true,
}) {
  const { isLiked, toggleLike } = useAppData();
  const liked = item ? isLiked(item) : false;

  const p = PRESET[variant] ?? PRESET.card;

  return (
    <button
      type="button"
      onClick={(e) => {
        if (stopPropagation) e.stopPropagation();
        if (!item?.itemKey) return;
        toggleLike(item);
      }}
      className={[
        "absolute z-10 rounded-full backdrop-blur border flex items-center justify-center",
        p.pos,
        p.btn,
        p.bg,
        className,
      ].join(" ")}
      aria-label={liked ? "unlike" : "like"}
    >
      <span
        className={[
          "flex items-center justify-center leading-none",
          liked ? `text-red-500 ${p.icon}` : `text-gray-500 ${p.icon}`,
        ].join(" ")}
      >
        {liked ? "♥" : "♡"}
      </span>
    </button>
  );
}
