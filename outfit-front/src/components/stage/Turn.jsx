import UserInputPreview from "./UserInputPreview";
import ResultCarousel from "./ResultCarousel";

const Turn = ({ turn, loading }) => {
  return (
    <div className="space-y-6">
      {/* 유저 입력 */}
      <UserInputPreview
        previewUrl={turn.input.previewUrl}
        textQuery={turn.input.textQuery}
      />

      {/* 결과 */}
      {turn.output ? (
        <ResultCarousel items={turn.output.items} loading={false} />
      ) : (
        <div className="text-gray-400 text-sm">추천 생성 중...</div>
      )}
    </div>
  );
};

export default Turn;
