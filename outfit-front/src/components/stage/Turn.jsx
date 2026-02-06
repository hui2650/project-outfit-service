import UserInputPreview from "./UserInputPreview";
import ResultCarousel from "./ResultCarousel";

const Turn = ({ turn, loading }) => {
  const isLoadingOnly = loading && !turn.output;
  const count = 30;
  const emojiList = ["👗", "👜", "👠", "👒", "🧥"];

  return (
    <div
      className={`${isLoadingOnly ? "h-screen flex flex-col items-center justify-center" : ""}`}
    >
      {turn.output ? (
        <div className="relative z-20">
          {/* 결과 */}
          <UserInputPreview
            previewUrl={turn.input.previewUrl}
            textQuery={turn.input.textQuery}
          />
          <ResultCarousel items={turn.output.items} loading={false} />
        </div>
      ) : (
        // 생성중
        <div className="h-full flex items-center justify-center text-gray-400 text-sm">
          추천 생성 중...
        </div>
      )}
      {isLoadingOnly && (
        <div className="absolute inset-0 overflow-hidden pointer-events-none z-10">
          {[...Array(30)].map((_, i) => {
            // 등간격을 기본으로 잡되, 약간의 무작위로 흔들어줌
            const base = (i / count) * 100;
            const offset = (Math.random() - 0.5) * (100 / count) * 0.7; // 흔들기 정도
            const left = base + offset;

            return (
              <span
                key={i}
                className="absolute text-2xl animate-emojiFall"
                style={{
                  top: `${Math.random() * -100}vh`, // -20vh ~ 0vh 사이에서 시작
                  left: `${left}%`,
                  animationDelay: `${Math.random() * 1}s`,
                  animationDuration: `${3 + Math.random() * 2}s`,
                }}
              >
                {emojiList[i % emojiList.length]}
              </span>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default Turn;
