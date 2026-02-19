import React from "react";
import ResultCard from "./ResultCard";
import { useLayout } from "../../store/layoutStore";

import { Swiper, SwiperSlide } from "swiper/react";
import { Scrollbar, Navigation, A11y } from "swiper/modules";
import "swiper/css";
import "swiper/css/scrollbar";
import "swiper/css/navigation";
import ResultModal from "../common/ResultModal";

const ResultCarousel = ({ items = [] }) => {
  const [selectedIndex, setSelectedIndex] = React.useState(null);
  const swiperRef = React.useRef(null);
  const scrollbarRef = React.useRef(null);
  const { panelCollapsed } = useLayout();

  React.useEffect(() => {
    if (swiperRef.current) swiperRef.current.slideTo(0, 0);
  }, [items]);

  return (
    // Swiper 전체를 360 제한 (핵심)
    <div className="relative mb-8 pt-3 sm:pt-4 w-full max-w-[300px] sm:max-w-none mr-auto">
      <Swiper
        modules={[Scrollbar, Navigation, A11y]}
        onSwiper={(swiper) => (swiperRef.current = swiper)}
        slidesPerGroup={1}
        spaceBetween={12}
        breakpoints={{
          320: { slidesPerView: 1 },
          480: { slidesPerView: 1 },
          640: { slidesPerView: 2, spaceBetween: 16 },
          768: { slidesPerView: 2.2, spaceBetween: 16 },
          1024: { slidesPerView: panelCollapsed ? 4 : 3, spaceBetween: 20 },
          1280: { slidesPerView: 4, spaceBetween: 24 },
        }}
        scrollbar={{
          draggable: true,
          el: scrollbarRef.current,
        }}
        navigation={{
          nextEl: ".swiper-button-next-custom",
          prevEl: ".swiper-button-prev-custom",
        }}
        className="pb-10 sm:pb-12 w-full"
      >
        {items.map((it, idx) => (
          <SwiperSlide key={it.itemKey || idx} className="h-auto">
            <div className="w-full">
              <ResultCard item={it} onClick={() => setSelectedIndex(idx)} />
            </div>
          </SwiperSlide>
        ))}
      </Swiper>

      <div
        ref={scrollbarRef}
        className="custom-scrollbar mt-3 sm:mt-4 w-full"
      />

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
