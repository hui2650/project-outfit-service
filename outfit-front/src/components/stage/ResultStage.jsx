import React from "react";
import Turn from "./Turn";
import EmptyResult from "./EmptyResult";

const ResultStage = ({ chatLogs, onSelectItem }) => {
  const bottomRef = React.useRef(null);

  // chatLogs가 바뀔 때마다 무조건 맨 아래로 이동
  React.useEffect(() => {
    bottomRef.current?.scrollIntoView({
      behavior: "smooth", // 부드럽게 내려감
      block: "end",
    });
  }, [chatLogs]);

  // 아직 아무 요청도 안 한 상태
  if (!chatLogs || chatLogs.length === 0) {
    return <EmptyResult />;
  }

  return (
    <div
      className=" h-full flex 
      items-center justify-center  overflow-y-auto px-4 [scrollbar-width:none] [-ms-overflow-style:none]"
      style={{ scrollbarGutter: "stable" }}
    >
      <div className="h-full w-full max-w-none  lg:max-w-7xl ">
        {chatLogs.length === 0 ? (
          <div className="h-full  flex flex-col items-center justify-center text-center">
            <h2 className="text-2xl font-bold text-foreground mb-3">
              AI 코디 추천을 시작해보세요
            </h2>
            <p className="text-muted-foreground max-w-md leading-relaxed mb-8">
              아이템 사진을 업로드하거나 텍스트로 설명해주세요. <br /> AI가
              당신에게 어울리는 코디를 추천해드립니다.
            </p>
          </div>
        ) : (
          <>
            {chatLogs.map((turn) => (
              <Turn key={turn.id} turn={turn} onSelectItem={onSelectItem} />
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
