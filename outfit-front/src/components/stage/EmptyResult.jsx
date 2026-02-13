// src/components/stage/EmptyResult.jsx
import React from "react";
import { useAppData } from "../../store/appDataStore";
import useTypewriter from "../../hooks/useTypewriter";

const EmptyResult = () => {
  const { guest } = useAppData();
  const nickname = guest?.nickname?.trim() || "게스트 사용자";

  // 기본멘트 (타이핑효과)
  const fullText = `${nickname}님, 안녕하세요.\nAI 코디 추천을 시작해보세요!`;
  const { out, done } = useTypewriter(fullText, {
    speed: 65,
    startDelay: 120,
    linePause: 300,
  });

  return (
    <div className="flex h-full w-full items-center justify-center px-4">
      <div className="text-center max-w-md">
        <h2
          className="
          text-2xl md:text-3xl
          text-foreground/95 font-medium mb-5
          whitespace-pre-line leading-snug
        "
        >
          {out}
          <span
            className={[
              "inline-block align-baseline ml-0.5",
              "w-[0.6ch] h-[1em]",
              "border-r-2 border-current",
              done ? "opacity-0" : "animate-blink",
            ].join(" ")}
            aria-hidden="true"
          />
        </h2>

        <p
          className={[
            "text-sm md:text-base",
            "text-muted-foreground leading-relaxed",
            "transition-opacity duration-500 delay-150",
            done ? "opacity-100" : "opacity-0",
          ].join(" ")}
        >
          오른쪽에서 아이템 이미지를 업로드하고
          <br />
          카테고리와 성별을 선택하면
          <br />
          AI가 어울리는 코디를 추천해드려요.
        </p>
      </div>
    </div>
  );
};

export default EmptyResult;
