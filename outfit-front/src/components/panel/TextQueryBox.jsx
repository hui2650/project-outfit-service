import React from "react";

const TextQueryBox = ({ textQuery, onTextQuery }) => {
  return (
    <div className="mt-8">
      <h3>또는 텍스트로 설명하세요</h3>
      <textarea
        className="mt-2 w-full h-24 border rounded-xl p-3 text-sm outline-none focus:ring-2 focus:ring-violet-200"
        placeholder='(예: "베이지 싱글코트")'
        value={textQuery}
        onChange={(e) => onTextQuery(e.target.value)}
      ></textarea>
    </div>
  );
};

export default TextQueryBox;
