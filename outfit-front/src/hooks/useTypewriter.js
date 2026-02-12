import React from "react";

/**
 * useTypewriter(text, options)
 * - text가 바뀌면 타이핑을 처음부터 다시 시작
 * - speed: 글자당 지연(ms)
 * - startDelay: 시작 전 지연(ms)
 *  - 줄바꿈(\n) 포함 텍스트 지원: 1줄 끝나면 linePause 만큼 쉬고 다음 줄 타이핑
 */
export default function useTypewriter(
  text,
  { speed = 45, startDelay = 120, linePause = 220 } = {},
) {
  const [out, setOut] = React.useState("");
  const [done, setDone] = React.useState(false);

  React.useEffect(() => {
    const lines = String(text ?? "").split("\n");
    let lineIdx = 0;
    let charIdx = 0;

    let tStart = null;
    let tTick = null;

    setOut("");
    setDone(false);

    const typeNext = () => {
      const currentLine = lines[lineIdx] ?? "";
      charIdx += 1;

      // 현재까지 출력될 문자열(이전 줄 + 현재 줄 일부)
      const typedLines = lines
        .slice(0, lineIdx)
        .concat(currentLine.slice(0, charIdx));

      setOut(typedLines.join("\n"));

      // 현재 줄 끝
      if (charIdx >= currentLine.length) {
        // 마지막 줄 끝이면 종료
        if (lineIdx >= lines.length - 1) {
          setDone(true);
          return;
        }
        // 다음 줄로
        lineIdx += 1;
        charIdx = 0;
        tTick = setTimeout(typeNext, linePause);
        return;
      }

      tTick = setTimeout(typeNext, speed);
    };

    tStart = setTimeout(() => {
      typeNext();
    }, startDelay);

    return () => {
      if (tStart) clearTimeout(tStart);
      if (tTick) clearTimeout(tTick);
    };
  }, [text, speed, startDelay, linePause]);

  return { out, done };
}
