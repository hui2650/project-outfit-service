import React from "react";

const ResultModal = ({ item, onClose }) => {
  // Esc로 닫기
  React.useEffect(() => {
    const onKeyDown = (e) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  // 모달 열릴 때 바디 스크롤 잠그기(선택)
  React.useEffect(() => {
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, []);

  return (
    <div className="fixed inset-0 z-50">
      {/* 어두운 배경 (클릭하면 닫힘) */}
      <div
        className="absolute inset-0 bg-black/60"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* 중앙 컨텐츠 */}
      <div className="relative h-full w-full flex items-center justify-center p-6">
        <div className="relative w-full max-w-5xl">
          {/* 닫기 버튼 */}
          <button
            type="button"
            onClick={onClose}
            className="absolute -top-12 right-0 text-white/90 hover:text-white text-3xl"
            aria-label="close"
          >
            ×
          </button>

          {/* 카드: 이미지 + 설명 */}
          <div className="bg-white rounded-2xl overflow-hidden shadow-xl grid grid-cols-1 md:grid-cols-[1fr_320px]">
            {/* 이미지 크게 */}
            <div className="bg-black">
              <img
                src={item.imageUrl}
                alt={item.title}
                className="w-full h-[70vh] object-contain bg-black"
              />
            </div>

            {/* 설명 박스 */}
            <div className="p-5 border-t md:border-t-0 md:border-l">
              <div className="text-xs text-gray-500 mb-2">
                Rank {item.rank} · Source: {item.source}
              </div>

              <div className="text-lg font-bold text-gray-900">
                {item.title || "Untitled"}
              </div>

              <div className="mt-3 text-sm text-gray-600 leading-relaxed">
                이 코디는 업로드한 아이템과 유사한 스타일로 추천된 이미지입니다.
                (추후 여기 영역에 “퍼컬/체형 기반 설명”을 붙이면 완성도가 확
                올라감)
              </div>

              {/* 액션 버튼(선택) */}
              <div className="mt-5 flex gap-2">
                <button
                  type="button"
                  className="px-4 py-2 rounded-lg bg-violet-600 text-white font-semibold"
                  onClick={() => {
                    // 나중에 “저장/좋아요” 같은 액션 붙일 자리
                    onClose();
                  }}
                >
                  확인
                </button>
                <button
                  type="button"
                  className="px-4 py-2 rounded-lg border"
                  onClick={onClose}
                >
                  닫기
                </button>
              </div>
            </div>
          </div>

          {/* 모달 아래 안내(선택) */}
          <div className="mt-3 text-center text-xs text-white/70">
            배경 클릭 또는 ESC로 닫기
          </div>
        </div>
      </div>
    </div>
  );
};

export default ResultModal;
