import React from "react";

const ChatPreview = ({ previewUrl, textQuery }) => {
  return (
    <div className="space-y-2">
      {previewUrl ? (
        <img
          src={previewUrl}
          alt="sent"
          className="w-full h-36 object-contain rounded-xl bg-card"
          onError={(e) => {
            e.currentTarget.style.display = "none";
          }}
        />
      ) : null}

      {textQuery?.trim() ? (
        <p className="mt-3 text-secondary-foreground">{textQuery.trim()}</p>
      ) : null}
    </div>
  );
};

export default ChatPreview;
