import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faClockRotateLeft } from "@fortawesome/free-solid-svg-icons";
import React from "react";

const HistoryChatListButton = ({ onClick }) => {
  return (
    <button
      type="button"
      onClick={onClick}
      className="h-10 w-10 rounded-xl border border-border bg-card hover:bg-muted flex items-center justify-center"
      title="이전 채팅"
    >
      <FontAwesomeIcon
        icon={faClockRotateLeft}
        className="text-foreground/80 text-lg"
      />
    </button>
  );
};

export default HistoryChatListButton;
