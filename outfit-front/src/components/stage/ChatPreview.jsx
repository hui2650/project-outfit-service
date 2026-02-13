// src/components/stage/ChatPreview.jsx
import React from "react";

const ChatPreview = ({ previewUrl, textQuery }) => {
  const hasSomething = previewUrl && textQuery && textQuery.trim().length > 0;

  return (
    <div className="ml-auto md:mr-4 mt-6 mb-8 w-fit max-w-[280px] md:max-w-[320px] bg-muted rounded-2xl shadow p-3 md:p-4">
      {previewUrl && (
        <img
          src={previewUrl}
          alt="sent"
          className="w-full h-32 md:h-36 object-contain rounded-xl bg-card"
        />
      )}

      {hasSomething && (
        <p className="mt-3 text-md md:text-base text-secondary-foreground break-words">
          {textQuery?.trim() ? textQuery : ""}
        </p>
      )}
    </div>
  );
};

export default ChatPreview;
