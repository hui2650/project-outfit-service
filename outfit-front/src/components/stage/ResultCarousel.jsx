import React from "react";
import ResultCard from "./ResultCard";
import ResultModal from "./ResultModal";
import { useLayout } from "../../store/layoutStore";

// Swiper
import { Swiper, SwiperSlide } from "swiper/react";
import { Scrollbar, Navigation, A11y } from "swiper/modules";
import "swiper/css";
import "swiper/css/scrollbar";

const PAGE_SIZE = 4;

function chunk(arr, size) {
  const out = [];
  for (let i = 0; i < arr.length; i += size) out.push(arr.slice(i, i + size));
  return out;
}

const ResultCarousel = ({ items = [] }) => {
  const [selectedIndex, setSelectedIndex] = React.useState(null);
  const swiperRef = React.useRef(null);

  const { panelCollapsed } = useLayout();

  // 패널 상태에 따라 그리드 클래스를 조정 (구조 유지)
  const gridClass = panelCollapsed
    ? "grid-cols-1 sm:grid-cols-2 lg:grid-cols-4"
    : "grid-cols-1 md:grid-cols-2 lg:grid-cols-4";

  const pages = React.useMemo(() => chunk(items, PAGE_SIZE), [items]);

  // items가 바뀌면 첫 페이지로 + 모달 닫기
  React.useEffect(() => {
    setSelectedIndex(null);
    if (swiperRef.current) {
      swiperRef.current.slideTo(0, 0); // 즉시 0번으로
    }
  }, [items]);

  const prev = () => swiperRef.current?.slidePrev();
  const next = () => swiperRef.current?.slideNext();

  const totalPages = Math.max(1, pages.length);

  return (
    <div className="w-full p-4 relative mb-8">
      <Swiper
        modules={[Scrollbar, Navigation, A11y]}
        onSwiper={(swiper) => (swiperRef.current = swiper)}
        slidesPerView={1}
        spaceBetween={24}
        // 스냅/드래그 부드럽게
        resistanceRatio={0.6}
        // ✅ 아래 긴 bar(드래그 가능)
        scrollbar={{
          draggable: true,
          el: ".result-swiper-scrollbar",
          dragClass: "result-swiper-scrollbar-drag",
        }}
        // 접근성
        a11y={{ enabled: true }}
      >
        {pages.map((pageItems, pageIdx) => (
          <SwiperSlide key={`page-${pageIdx}`}>
            <div className={`grid ${gridClass} gap-6`}>
              {pageItems.map((it, i) => {
                const realIndex = pageIdx * PAGE_SIZE + i;
                return (
                  <ResultCard
                    key={it.itemKey || realIndex}
                    item={it}
                    onClick={() => setSelectedIndex(realIndex)}
                  />
                );
              })}

              {/* 빈칸 채우기: lg에서 4열일 때만 필요 */}
              {pageItems.length < PAGE_SIZE &&
                Array.from({ length: PAGE_SIZE - pageItems.length }).map(
                  (_, i) => (
                    <div
                      key={`empty-${pageIdx}-${i}`}
                      className="h-[360px] rounded-2xl bg-transparent hidden lg:block"
                    />
                  ),
                )}
            </div>

            <div className="result-swiper-scrollbar mt-6" />
          </SwiperSlide>
        ))}
      </Swiper>

      {/* 좌우 버튼 (Swiper 제어) */}
      <button
        type="button"
        onClick={prev}
        disabled={totalPages <= 1}
        className="absolute left-0 top-1/2 -translate-y-1/2 px-3 h-9 rounded-lg border bg-card disabled:opacity-30 z-10"
      >
        ‹
      </button>

      <button
        type="button"
        onClick={next}
        disabled={totalPages <= 1}
        className="absolute right-0 top-1/2 -translate-y-1/2 px-3 h-9 rounded-lg border bg-card disabled:opacity-30 z-10"
      >
        ›
      </button>

      {/* 모달 */}
      {selectedIndex !== null && (
        <ResultModal
          items={items}
          index={selectedIndex}
          onClose={() => setSelectedIndex(null)}
          onChangeIndex={setSelectedIndex}
        />
      )}
    </div>
  );
};

export default ResultCarousel;
