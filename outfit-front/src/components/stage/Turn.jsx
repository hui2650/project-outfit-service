import React from "react";
import ResultCarousel from "./ResultCarousel";
import OutfitLoadingMark from "../common/OutfitLoadingMark";
import AIMessage from "./AIMessage";
import ChatPreview from "./ChatPreview";

const Turn = ({ turn, onSelectItem }) => {
  /* ===============================
     로딩 전용 Turn
     =============================== */
  if (turn.status === "loading") {
    return (
      <div className="w-full h-[calc(100vh-54px)] flex-1 flex items-center justify-center">
        <OutfitLoadingMark />
      </div>
    );
  }

  /* ===============================
     일반 Turn (채팅 렌더)
     =============================== */
  return (
    <div className="w-full">
      {turn.messages.map((msg) => {
        // 유저 입력 미리보기
        if (msg.type === "input") {
          return (
            <ChatPreview
              key={msg.id}
              previewUrl={msg.previewUrl}
              textQuery={msg.text}
            />
          );
        }

        // 텍스트 메시지
        if (msg.type === "text") {
          return (
            <AIMessage key={msg.id} content={msg.content} role={msg.role} />
          );
        }

        // 결과 캐러셀
        if (msg.type === "carousel") {
          return (
            <ResultCarousel key={msg.id} items={msg.items} loading={false} />
          );
        }

        // 에러
        if (msg.type === "error") {
          return (
            <AIMessage key={msg.id} content={msg.message} variant="error" />
          );
        }

        return null;
      })}
    </div>
  );
};

export default Turn;
