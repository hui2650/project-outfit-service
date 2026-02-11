import React from "react";
import { useAppData } from "../../store/appDataStore.jsx";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faPenToSquare } from "@fortawesome/free-solid-svg-icons";

const NewChatButton = ({ className = "" }) => {
  const { createNewSession } = useAppData();

  const handleNewChat = React.useCallback(() => {
    // ✅ 기존 채팅은 chatSessions에 남아있고,
    // ✅ currentSessionId만 새 세션으로 바뀌면서 화면이 초기화됨
    createNewSession();
  }, [createNewSession]);

  return (
    <button
      type="button"
      onClick={handleNewChat}
      className="h-10 w-10 rounded-xl border border-border bg-card hover:bg-muted flex items-center justify-center relative"
      aria-label="새 채팅 시작"
      title="새 채팅하기"
    >
      <FontAwesomeIcon
        icon={faPenToSquare}
        className="text-foreground/80 text-lg absolute left-2.5"
      />
    </button>
  );
};

export default NewChatButton;
