import React from "react";
import ResultCard from "./ResultCard";
import { useLayout } from "../../store/layoutStore";

// Swiper
import { Swiper, SwiperSlide } from "swiper/react";
import { Scrollbar, Navigation, A11y } from "swiper/modules";
import "swiper/css";
import "swiper/css/scrollbar";
import "swiper/css/navigation"; // 네비게이션 CSS 추가
import ResultModal from "../common/ResultModal";

const ResultCarousel = ({ items = [] }) => {
  const [selectedIndex, setSelectedIndex] = React.useState(null);
  const swiperRef = React.useRef(null);
  const { panelCollapsed } = useLayout();

  // items가 바뀌면 첫 슬라이드로 이동
  React.useEffect(() => {
    if (swiperRef.current) {
      swiperRef.current.slideTo(0, 0);
    }
  }, [items]);

  return (
    <div className="w-full p-4 relative mb-8 group">
      <Swiper
        modules={[Scrollbar, Navigation, A11y]}
        onSwiper={(swiper) => (swiperRef.current = swiper)}
        // 핵심: 한 번에 하나씩 넘기기 위한 설정
        slidesPerGroup={1}
        spaceBetween={24}
        // 반응형 지점 설정 (기존 gridClass 로직을 Swiper 옵션으로 대체)
        breakpoints={{
          320: { slidesPerView: 1 },
          640: { slidesPerView: 2 },
          1024: { slidesPerView: panelCollapsed ? 4 : 3 }, // 패널 상태에 따라 조절
          1280: { slidesPerView: 4 },
        }}
        scrollbar={{
          draggable: true,
          el: ".custom-scrollbar",
          dragClass: "custom-scrollbar-drag",
        }}
        navigation={{
          nextEl: ".swiper-button-next-custom",
          prevEl: ".swiper-button-prev-custom",
        }}
        className="pb-12" // 하단 스크롤바 공간 확보
      >
        {items.map((it, idx) => (
          <SwiperSlide key={`${it.itemKey || it.imageUrl || it.landingUrl}-${idx}`}>
            <ResultCard item={it} onClick={() => setSelectedIndex(idx)} />
          </SwiperSlide>
        ))}
      </Swiper>

      {/* 커스텀 스크롤바 (슬라이더 하단) */}
      <div className="custom-scrollbar mt-4 mx-auto w-full" />

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
