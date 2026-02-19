import React from "react";
import { useAppData } from "../../store/appDataStore.jsx";
import LikeButton from "./LikeButton.jsx";

const ResultModal = ({ items, index, onClose, onChangeIndex }) => {
  const item = items?.[index];

  const { isLiked } = useAppData();
  const liked = item ? isLiked(item) : false;

  const prev = React.useCallback(() => {
    if (index > 0) onChangeIndex(index - 1);
  }, [index, onChangeIndex]);

  const next = React.useCallback(() => {
    if (index < (items?.length ?? 0) - 1) onChangeIndex(index + 1);
  }, [index, items?.length, onChangeIndex]);

  // Esc/Arrow navigation
  React.useEffect(() => {
    const onKeyDown = (e) => {
      if (e.key === "Escape") onClose?.();
      if (e.key === "ArrowLeft") prev();
      if (e.key === "ArrowRight") next();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose, prev, next]);

  // body scroll lock (모달 열렸을 때만)
  React.useEffect(() => {
    if (!item) return;
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prevOverflow;
    };
  }, [item]);

  if (!item) return null;

  const isFirst = index === 0;
  const isLast = index === (items?.length ?? 0) - 1;

  return (
    <div className="fixed inset-0 z-[1000]">
      {/* Backdrop */}
      <button
        type="button"
        className="absolute inset-0 bg-foreground/60"
        onClick={onClose}
        aria-label="close backdrop"
      />

      {/* Content wrapper */}
      <div className="relative h-full w-full flex items-center justify-center p-4 sm:p-6">
        <div className="relative w-full max-w-5xl">
          {/* Close */}
          <button
            type="button"
            onClick={onClose}
            className={[
              "absolute z-20",
              "hidden md:block",
              "sm:top-3 sm:right-3 md:-top-12 md:right-0",
              "h-10 w-10 sm:h-11 sm:w-11",
              "text-white text-2xl leading-none",
              "flex items-center justify-center",
            ].join(" ")}
            aria-label="close"
            title="닫기"
          >
            ×
          </button>

          {/* Card */}
          <div
            className={[
              "bg-card rounded-2xl overflow-hidden shadow-xl",
              "grid grid-cols-1 md:grid-cols-[1fr_320px] relative",
              // 모바일에서 화면 꽉 차지 않게 max height 관리
              "max-h-[92vh] md:max-h-none",
            ].join(" ")}
          >
            {/* Image */}
            <div className="relative bg-black">
              <img
                src={item.imageUrl}
                alt={item.title || "item"}
                className={[
                  "w-full object-contain bg-black",
                  // 모바일: 이미지 영역을 너무 길게 잡지 않기
                  "h-[56vh] sm:h-[60vh] md:h-[70vh]",
                ].join(" ")}
              />

              {/* Like button overlay */}
              <LikeButton item={item} variant="modal" />
              {/* Prev / Next (모바일 터치 영역 확대) */}
              <button
                type="button"
                onClick={prev}
                disabled={isFirst}
                className={[
                  "absolute z-20",
                  "left-2 sm:left-3 md:left-4",
                  "top-1/2",
                  "-translate-y-1/2",
                  "h-10 w-10 sm:h-11 sm:w-11",
                  "rounded-full",
                  "bg-black/20 hover:bg-black/35",
                  "text-white text-lg",
                  "flex items-center justify-center",
                  "transition",
                  "disabled:opacity-30 disabled:hover:bg-black/40",
                ].join(" ")}
                aria-label="prev"
                title="이전"
              >
                ←
              </button>

              <button
                type="button"
                onClick={next}
                disabled={isLast}
                className={[
                  "absolute z-20",
                  "right-2 sm:right-3 md:right-4",
                  "top-1/2",
                  "-translate-y-1/2",
                  "h-10 w-10 sm:h-11 sm:w-11",
                  "rounded-full",
                  "bg-black/20 hover:bg-black/35",
                  "text-white text-lg",
                  "flex items-center justify-center",
                  "transition",
                  "disabled:opacity-30 disabled:hover:bg-black/40",
                ].join(" ")}
                aria-label="next"
                title="다음"
              >
                →
              </button>
            </div>

            {/* Info */}
            <div
              className={[
                "p-4 sm:p-5",
                "border-t md:border-t-0 md:border-l border-border",
                // 모바일에서 설명 영역 자체 스크롤 허용 (이미지+설명 합쳐 92vh 안에 들어가게)
                "max-h-[36vh] md:max-h-none",
                "overflow-y-auto",
              ].join(" ")}
            >
              <div className="text-xs text-muted-foreground mb-2">
                Source: {item.source}
              </div>

              <div className="text-base sm:text-lg font-bold text-foreground break-words">
                {item.title || "Untitled"}
              </div>

              <div className="mt-3 text-sm text-muted-foreground leading-relaxed">
                이 코디는 업로드한 아이템과 유사한 스타일로 추천된 이미지입니다.
              </div>

              <div className="mt-5 flex gap-2">
                <button
                  type="button"
                  className="w-full md:w-auto px-4 py-2.5 rounded-xl bg-primary/90 text-primary-foreground font-semibold hover:opacity-90 transition"
                  onClick={onClose}
                >
                  확인
                </button>
                <button
                  type="button"
                  onClick={onClose}
                  className={[
                    "w-full md:w-auto px-4 py-2.5 rounded-xl bg-foreground/25 text-primary-foreground font-semibold hover:opacity-90 transition",
                  ].join(" ")}
                  aria-label="close"
                  title="닫기"
                >
                  닫기
                </button>
              </div>
            </div>
          </div>

          <div className="mt-3 text-center text-xs text-white/70">
            닫기 버튼 또는 ESC로 닫기 · ← → 로 넘기기
          </div>
        </div>
      </div>
    </div>
  );
};

export default ResultModal;
