// src/components/stage/ResultStage.jsx
import React from "react";
import Turn from "./Turn";
import EmptyResult from "./EmptyResult";
import ChatComposer from "./ChatComposer";
import { useChatPage } from "../../pages/chat/ChatPageContext";

const ResultStage = ({ chatLogs, onSelectItem, onSendChat, chatDisabled }) => {
  const bottomRef = React.useRef(null);
  const safeLogs = Array.isArray(chatLogs) ? chatLogs : [];

  const { emptyReloadKey } = useChatPage();

  const isOnlyLoading =
    safeLogs.length === 1 && safeLogs[0].status === "loading";

  React.useEffect(() => {
    bottomRef.current?.scrollIntoView({
      behavior: "smooth",
      block: "end",
      inline: "nearest",
    });
  }, [safeLogs]);

  if (safeLogs.length === 0) {
    return (
      <div className="flex-1 flex flex-col">
        <div className="flex-1 flex items-center justify-center">
          <EmptyResult key={emptyReloadKey} />
        </div>
        <ChatComposer disabled={true} onSend={onSendChat} />
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col min-h-0">
      {/* 스크롤 영역 */}
      <div
        className={[
          "h-full",
          "px-4 sm:px-6 lg:px-8", // 모바일 표준
          isOnlyLoading
            ? "overflow-hidden"
            : "overflow-y-auto [scrollbar-width:none] [-ms-overflow-style:none]",
        ].join(" ")}
        style={{ scrollbarGutter: "stable" }}
      >
        <div className="w-full max-w-none lg:max-w-7xl mx-auto">
          {safeLogs.map((turn) => (
            <Turn key={turn.id} turn={turn} onSelectItem={onSelectItem} />
          ))}
          <div className="h-24" ref={bottomRef} />
        </div>

        <ChatComposer disabled={chatDisabled} onSend={onSendChat} />
      </div>
    </div>
  );
};

export default ResultStage;
