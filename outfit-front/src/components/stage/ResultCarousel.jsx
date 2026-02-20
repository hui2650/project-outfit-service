import React from 'react'
import ResultCard from './ResultCard'
import { useLayout } from '../../store/layoutStore'

import { Swiper, SwiperSlide } from 'swiper/react'
import { Scrollbar, Navigation, A11y } from 'swiper/modules'
import 'swiper/css'
import 'swiper/css/scrollbar'
import 'swiper/css/navigation'
import ResultModal from '../common/ResultModal'

/**
 * ResultCarousel (추천 결과 리스트를 스와이프 캐러셀로)
 * - 프로젝트 핵심 UX: 추천된 코디 이미지 여러 장을 빠르게 훑고 저장/확대
 * - panelCollapsed(오른쪽 패널 접힘 여부)에 따라 슬라이드 개수 조절
 * - items가 바뀌면 첫 페이지로 다시 이동(slideTo(0))
 * - 커스텀 scrollbarRef로 Swiper 스크롤바를 밖으로 빼서 UI 깔끔하게
 */

const ResultCarousel = ({ items = [] }) => {
  const [selectedIndex, setSelectedIndex] = React.useState(null) // 모달 인덱스
  const swiperRef = React.useRef(null)
  const scrollbarRef = React.useRef(null)
  const { panelCollapsed } = useLayout()

  // 새로운 추천 결과가 들어오면 캐러셀을 처음으로 리셋
  React.useEffect(() => {
    if (swiperRef.current) swiperRef.current.slideTo(0, 0)
  }, [items])

  return (
    // 모바일에서 너무 넓지 않게 max-width 제한 + 왼쪽 정렬 (mr-auto)
    <div className="relative mb-8 pt-3 sm:pt-4 w-full max-w-[300px] sm:max-w-none mr-auto">
      <Swiper
        modules={[Scrollbar, Navigation, A11y]}
        onSwiper={(swiper) => (swiperRef.current = swiper)}
        slidesPerGroup={1}
        spaceBetween={12}
        breakpoints={{
          // 반응형: 화면 크기에 따라 slidesPerView 조절
          320: { slidesPerView: 1 },
          480: { slidesPerView: 1 },
          640: { slidesPerView: 2, spaceBetween: 16 },
          768: { slidesPerView: 2.2, spaceBetween: 16 },
          1024: { slidesPerView: panelCollapsed ? 4 : 3, spaceBetween: 20 },
          1280: { slidesPerView: 4, spaceBetween: 24 },
        }}
        scrollbar={{
          draggable: true, // 드래그 가능한 스크롤바
          el: scrollbarRef.current, // 밖으로 뺀 DOM을 스크롤바로 사용
        }}
        navigation={{
          nextEl: '.swiper-button-next-custom',
          prevEl: '.swiper-button-prev-custom',
        }}
        className="pb-10 sm:pb-12 w-full"
      >
        {items.map((it, idx) => (
          <SwiperSlide key={it.itemKey || idx} className="h-auto">
            <div className="w-full">
              {/* 카드 클릭하면 모달로 상세 보기 */}
              <ResultCard item={it} onClick={() => setSelectedIndex(idx)} />
            </div>
          </SwiperSlide>
        ))}
      </Swiper>

      {/* 커스텀 스크롤바 DOM */}
      <div
        ref={scrollbarRef}
        className="custom-scrollbar mt-3 sm:mt-4 w-full"
      />

      {/* 모달: selectedIndex가 있을 때만 렌더 */}
      {selectedIndex !== null && (
        <ResultModal
          items={items}
          index={selectedIndex}
          onClose={() => setSelectedIndex(null)}
          onChangeIndex={setSelectedIndex}
        />
      )}
    </div>
  )
}

export default ResultCarousel
