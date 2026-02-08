import UserInputPreview from './UserInputPreview'
import ResultCarousel from './ResultCarousel'
import OutfitLoadingMark from './OutfitLoadingMark'
import AIMessage from './AIMessage'

<<<<<<< HEAD
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
=======
const Turn = ({ turn, onSelectItem }) => {
  /* ===============================
     1️⃣ 로딩 전용 Turn
     =============================== */
  if (turn.status === 'loading') {
    return (
      <div className="w-full h-full min-h-[240px] flex items-center justify-center">
        <OutfitLoadingMark />
      </div>
    )
  }

  /* ===============================
     2️⃣ 일반 Turn (채팅 렌더)
     =============================== */
  return (
    <div className="w-full">
      {turn.messages.map((msg) => {
        // 유저 입력 미리보기
        if (msg.type === 'input') {
          return (
            <UserInputPreview
              key={msg.id}
              previewUrl={msg.previewUrl}
              textQuery={msg.text}
            />
          )
        }

        // 텍스트 메시지 (유저 / AI)
        if (msg.type === 'text') {
          return (
            <AIMessage key={msg.id} content={msg.content} role={msg.role} />
          )
        }

        // 결과 캐러셀
        if (msg.type === 'carousel') {
          return (
            <ResultCarousel
              key={msg.id}
              items={msg.items}
              loading={false}
              onSelectItem={(item) =>
                onSelectItem(
                  turn.id,
                  msg.requestId,
                  item,
                  turn.input.file,
                  turn.input.category,
                  turn.input.gender
                )
              }
            />
          )
        }

        // 에러
        if (msg.type === 'error') {
          return (
            <AIMessage key={msg.id} content={msg.message} variant="error" />
          )
        }

        return null
      })}
>>>>>>> feature/taehui/default-uI
    </div>
  )
}

export default Turn
