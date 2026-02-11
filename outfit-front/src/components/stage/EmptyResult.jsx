// src/components/stage/EmptyResult.jsx
import React from "react";

const EmptyResult = () => {
  return (
    <div className="flex h-full w-full items-center justify-center">
      <div className="text-center max-w-md">
        <h2 className="text-2xl text-foreground font-bold mb-3">
          AI 코디 추천을 시작해보세요
        </h2>

        <p className="text-muted-foreground leading-relaxed">
          오른쪽에서 아이템 이미지를 업로드하고
          <br />
          카테고리와 성별을 선택하면
          <br />
          AI가 어울리는 코디를 추천해드려요.
        </p>

        <div className="mt-8 text-sm text-muted-foreground">
          ⟶ 먼저 아이템을 입력해보세요
        </div>
      </div>
    </div>
  );
};

export default EmptyResult;
