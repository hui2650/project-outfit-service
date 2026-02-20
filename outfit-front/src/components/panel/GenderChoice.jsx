/*
GenderChoice
- 추천 검색 조건에 포함되는 성별 선택 UI
- 값(man/woman)은 FastAPI에 전달되는 gender와 계약된 문자열을 사용
*/

const GenderChoice = ({ gender, onChangeGender }) => {
  const genders = ['man', 'woman']

  return (
    <div className="flex gap-2 mt-8 mb-4 flex-wrap">
      {genders.map((g) => (
        <button
          key={g}
          type="button"
          className={`text-xs md:text-sm px-3 py-1.5 rounded-full border transition-colors duration-150 ${
            gender === g
              ? 'bg-gradient-to-r from-primary/90 to-accent/90 text-white'
              : 'bg-secondary text-secondary-foreground border-gray-300 hover:bg-primary/10 hover:text-primary'
          }`}
          onClick={() => onChangeGender(g)}
        >
          {g}
        </button>
      ))}
    </div>
  )
}

export default GenderChoice
