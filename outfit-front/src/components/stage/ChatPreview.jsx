import React from "react";

const ChatPreview = ({ previewUrl, textQuery }) => {
  const hasSomething = previewUrl || (textQuery && textQuery.trim().length > 0);

  return (
    <div className="ml-auto mr-4 mt-6 w-fit max-w-[320px] bg-white rounded-2xl shadow p-4 border">
      <div className="text-xs text-gray-500"></div>

      {previewUrl ? (
        <img
          src={previewUrl}
          alt="sent"
          className="w-full h-36 object-contain rounded-xl bg-gray-50"
        />
      ) : (
        <div className="text-sm text-gray-400">이미지 없음</div>
      )}

      <div className="mt-3 text-sm">
        {hasSomething ? (
          <span className="text-gray-700">
            {textQuery?.trim() ? textQuery : ""}
          </span>
        ) : (
          <span className="text-gray-400">아직 입력 없음</span>
        )}
      </div>
    </div>
  );
};

export default ChatPreview;
