// src/components/stage/ResultCarousel.jsx
import React from "react";
import ResultCard from "./ResultCard";
import ResultModal from "./ResultModal";
import { useLayout } from "../../store/layoutStore";

const PAGE_SIZE = 4;

const ResultCarousel = ({ loading, items = [] }) => {
  const [page, setPage] = React.useState(0);
  const [selectedIndex, setSelectedIndex] = React.useState(null);

  const { panelCollapsed } = useLayout();

  const gridClass = panelCollapsed
    ? "grid-cols-1 sm:grid-cols-2 lg:grid-cols-4"
    : "grid-cols-1 lg:grid-cols-2 2xl:grid-cols-3";

  const totalPages = Math.max(1, Math.ceil(items.length / PAGE_SIZE));
  const start = page * PAGE_SIZE;
  const visible = items.slice(start, start + PAGE_SIZE);

  React.useEffect(() => {
    setPage(0);
  }, [items]);

  const prev = () => setPage((p) => Math.max(0, p - 1));
  const next = () => setPage((p) => Math.min(totalPages - 1, p + 1));

  return (
    <div className="w-full p-4 relative">
      {loading ? (
        <div className="grid grid-cols-4 gap-6">
          {Array.from({ length: 4 }).map((_, i) => (
            <div
              key={i}
              className="h-[360px] rounded-2xl bg-muted animate-pulse"
            />
          ))}
        </div>
      ) : (
        <>
          <div className={`grid ${gridClass} gap-6`}>
            {visible.map((it, i) => {
              const realIndex = start + i;

              return (
                <ResultCard
                  key={it.itemKey || realIndex}
                  item={it}
                  onClick={() => setSelectedIndex(realIndex)}
                />
              );
            })}

            {visible.length < 4 &&
              Array.from({ length: 4 - visible.length }).map((_, i) => (
                <div
                  key={`empty-${i}`}
                  className="h-[360px] rounded-2xl bg-transparent"
                />
              ))}
          </div>

          {/* 좌우 버튼 */}
          <button
            type="button"
            onClick={prev}
            disabled={page === 0}
            className="absolute left-0 top-1/2 -translate-y-1/2 px-3 h-9 rounded-lg border bg-card disabled:opacity-30"
          >
            ‹
          </button>

          <button
            type="button"
            onClick={next}
            disabled={page === totalPages - 1}
            className="absolute right-0 top-1/2 -translate-y-1/2 px-3 h-9 rounded-lg border bg-card disabled:opacity-30"
          >
            ›
          </button>
        </>
      )}

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
