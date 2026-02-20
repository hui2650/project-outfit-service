/*
SubmitButton
- 입력값 충족 여부(isReadyToSubmit)와 로딩 상태(loading)에 따라 비활성/문구를 제어
- 준비되지 않은 상태에서는 안내 문구를 툴팁처럼 노출
*/

const SubmitButton = ({ loading, onSubmit, isReadyToSubmit }) => {
  const disabled = loading || !isReadyToSubmit

  return (
    <div className="relative group w-full mt-4">
      <button
        className={`mt-4 w-full rounded-xl py-3 font-semibold transition-all duration-200 shadow-lg text-sm md:text-base
    ${
      disabled
        ? 'bg-gradient-to-r from-primary/90 to-accent/90 text-white/70 cursor-not-allowed opacity-60'
        : 'bg-gradient-to-r from-primary to-accent text-white  hover:brightness-110 shadow-[0_4px_14px_rgba(124,58,237,0.15)] active:scale-[0.98]'
    }`}
        onClick={onSubmit}
        disabled={disabled}
        type="button"
      >
        {loading ? '추천 생성 중...' : '코디 추천받기'}
      </button>

      {!isReadyToSubmit && !loading && (
        <div className="absolute left-0 -bottom-9 whitespace-nowrap rounded-md px-2 py-1 text-xs text-gray-500 z-10">
          ※ 이미지와 성별, 카테고리를 모두 선택해주세요
        </div>
      )}
    </div>
  )
}

export default SubmitButton
