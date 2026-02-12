import React from "react";

const ChatPreview = ({ previewUrl, textQuery }) => {
  const hasSomething = previewUrl && textQuery && textQuery.trim().length > 0;

  return (
    <div className="ml-auto mr-4 mt-6 mb-8 w-fit max-w-[320px] bg-muted rounded-2xl shadow p-4">
      <div className="text-xs text-gray-500"></div>

      {previewUrl && (
        <img
          src={previewUrl}
          alt="sent"
          className="w-full h-36 object-contain rounded-xl bg-card"
        />
      )}

      {/* 텍스트 있는 경우에만 */}
      {hasSomething && (
        <p className="mt-3 text-secondary-foreground">
          {textQuery?.trim() ? textQuery : ""}
        </p>
      )}
    </div>
  );
};

export default ChatPreview;
