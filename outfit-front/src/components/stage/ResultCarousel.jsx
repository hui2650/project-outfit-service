import React from "react";
import ResultCard from "./ResultCard";
import ResultModal from "./ResultModal";

const PAGE_SIZE = 4;

const ResultCarousel = ({ loading, items = [] }) => {
  const [page, setPage] = React.useState(0);
  const [selected, setSelected] = React.useState(null);

  const totalPages = Math.max(1, Math.ceil(items.length / PAGE_SIZE));
  const start = page * PAGE_SIZE;
  const visible = items.slice(start, start + PAGE_SIZE);

  // items가 새로 들어오면 page를 0으로 돌리는 게 보통 UX가 좋음
  React.useEffect(() => {
    setPage(0);
  }, [items]);

  const prev = () => setPage((p) => Math.max(0, p - 1));
  const next = () => setPage((p) => Math.min(totalPages - 1, p + 1));

  return (
    <div className="w-full p-4 relative">
      {/* 로딩 처리 */}
      {loading ? (
        <div className="grid grid-cols-4 gap-6">
          {Array.from({ length: 4 }).map((_, i) => (
            <div
              key={i}
              className="h-[360px] rounded-2xl bg-gray-100 animate-pulse"
            />
          ))}
        </div>
      ) : (
        <>
          {/* 카드 4장: 화면 꽉 채우기 */}
          <div className="grid grid-cols-4 gap-6">
            {visible.map((it) => (
              <ResultCard
                key={it.rank}
                item={it}
                onClick={() => setSelected(it)}
              />
            ))}

            {/* 8개가 아닐 때(안전) 빈 칸 채우기 */}
            {visible.length < 4 &&
              Array.from({ length: 4 - visible.length }).map((_, i) => (
                <div
                  key={`empty-${i}`}
                  className="h-[360px] rounded-2xl bg-transparent"
                />
              ))}
          </div>

          {/* dots: 페이지 수만큼 */}
          <div className="mt-6 flex justify-center gap-2">
            {Array.from({ length: totalPages }).map((_, i) => (
              <button
                key={i}
                type="button"
                onClick={() => setPage(i)}
                className={`h-2 rounded-full transition-all ${
                  i === page ? "w-10 bg-violet-600" : "w-3 bg-violet-200"
                }`}
                aria-label={`page-${i + 1}`}
              />
            ))}
          </div>
          {/* 버튼 */}
          <button
            type="button"
            onClick={prev}
            disabled={page === 0 || loading || items.length === 0}
            className="h-9 px-3 absolute left-0 top-1/2 -translate-y-1/2 rounded-lg border bg-white disabled:opacity-80"
          >
            ‹
          </button>
          <button
            type="button"
            onClick={next}
            disabled={page === totalPages - 1 || loading || items.length === 0}
            className="h-9 px-3 absolute right-0 top-1/2 -translate-y-1/2 rounded-lg border bg-white disabled:opacity-40"
          >
            ›
          </button>
        </>
      )}

      {/* 모달 */}
      {selected && (
        <ResultModal item={selected} onClose={() => setSelected(null)} />
      )}
    </div>
  );
};

export default ResultCarousel;
