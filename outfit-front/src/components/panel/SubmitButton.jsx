// 로딩상태에 따른 조건부 스타일링

//SubmitButton을 누르면
// file + textQuery를 FormData로 묶어서
// Spring API로 보내고
// 응답으로 받은 items를 state에 넣어서
// ResultCarousel이 그리게 만드는 것

const SubmitButton = ({ loading, onSubmit, isReadyToSubmit }) => {
<<<<<<< HEAD
  const disabled = loading || !isReadyToSubmit;
=======
  const disabled = loading || !isReadyToSubmit
>>>>>>> feature/taehui/default-uI
  return (
    <div className="relative group w-full mt-4">
      <button
        className={`w-full rounded-xl mt-4 py-3 font-semibold transition-all duration-200 ${
          disabled
<<<<<<< HEAD
            ? "bg-primary text-primary-foreground opacity-50 cursor-not-allowed"
            : "bg-primary text-primary-foreground hover:brightness-110"
=======
            ? 'bg-primary text-primary-foreground opacity-50 cursor-not-allowed'
            : 'bg-primary text-primary-foreground hover:brightness-110'
>>>>>>> feature/taehui/default-uI
        }`}
        onClick={onSubmit}
        disabled={disabled}
        type="button"
      >
<<<<<<< HEAD
        {loading ? "추천 생성 중..." : "✨ 코디 추천받기"}
=======
        {loading ? '추천 생성 중...' : '코디 추천받기'}
>>>>>>> feature/taehui/default-uI
        {/* 툴팁 - disabled 상태에서는 button이 pointer-events: none 이라 별도 div로 */}
      </button>
      {!isReadyToSubmit && !loading && (
        <div className="absolute left-0 -bottom-9 whitespace-nowrap rounded-md  px-2 py-1 text-xs text-gray-500 z-10">
<<<<<<< HEAD
          ※ 이미지와 카테고리를 모두 선택해주세요
        </div>
      )}
    </div>
  );
};
=======
          ※ 이미지와 성별, 카테고리를 모두 선택해주세요
        </div>
      )}
    </div>
  )
}
>>>>>>> feature/taehui/default-uI

export default SubmitButton
