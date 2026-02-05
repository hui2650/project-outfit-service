// 로딩상태에 따른 조건부 스타일링

//SubmitButton을 누르면
// file + textQuery를 FormData로 묶어서
// Spring API로 보내고
// 응답으로 받은 items를 state에 넣어서
// ResultCarousel이 그리게 만드는 것

const SubmitButton = ({ loading, onSubmit }) => {
  return (
    <button
      className={`w-full rounded-xl mt-4 py-3 font-semibold ${
        loading
          ? "bg-primary text-primary-foreground  opacity-50 cursor-not-allowed"
          : "bg-primary text-primary-foreground "
      }`}
      onClick={onSubmit}
      disabled={loading}
      type="button"
    >
      {loading ? "추천 생성 중..." : "✨ 코디 추천받기"}
    </button>
  );
};

export default SubmitButton;
