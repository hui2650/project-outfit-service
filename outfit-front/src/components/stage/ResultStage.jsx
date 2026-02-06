// 왼쪽영역
// itmes를 받아서 ResultCarousel 렌더
// ChatPreview(말풍선) 렌더

// 나중에
// turns.map(turn =>
//   <Turn
//     input={<ChatPreview ... />}
//     output={<ResultCarousel ... />}
//   />
// )

import React from "react";
import Turn from "./Turn";

const ResultStage = ({ loading, chatLogs }) => {
  const bottomRef = React.useRef(null);

  // ✅ chatLogs가 바뀔 때마다 무조건 맨 아래로 이동
  React.useEffect(() => {
    bottomRef.current?.scrollIntoView({
      behavior: "smooth", // 부드럽게 내려감
      block: "end",
    });
  }, [chatLogs]);

  return (
    <div
      className=" h-full max-w-7xl overflow-y-auto px-4 [scrollbar-width:none] [-ms-overflow-style:none]"
      style={{ scrollbarGutter: "stable" }}
    >
      <div className="h-full">
        {chatLogs.length === 0 ? (
          <div className="h-full flex items-center justify-center text-gray-400">
            코디 추천을 시작해보세요
          </div>
        ) : (
          <>
            {chatLogs.map((turn) => (
              <Turn key={turn.id} turn={turn} loading={loading} />
            ))}
            {/* 맨 아래 기준점 */}
            <div ref={bottomRef} />
          </>
        )}
      </div>
    </div>
  );
};

export default ResultStage;
