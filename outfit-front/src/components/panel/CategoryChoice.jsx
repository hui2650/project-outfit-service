/*
CategoryChoice
- 추천에 필요한 카테고리 선택 UI
- 내부 값(top/bottom/...)은 FastAPI에 전달되는 category와 계약된 문자열을 사용
*/

const CategoryChoice = ({ category, onChangeCategory }) => {
  const categories = [
    'top',
    'bottom',
    'skirt',
    'dress',
    'outer',
    'shoes',
    'bag',
  ]

  return (
    <div className="flex gap-2 mt-4 flex-wrap">
      {categories.map((c) => (
        <button
          key={c}
          type="button"
          className={`text-xs md:text-sm px-3 py-1.5 rounded-full border transition-colors duration-150 ${
            category === c
              ? 'bg-gradient-to-r from-primary/90 to-accent/90 text-white '
              : 'bg-secondary text-secondary-foreground border-gray-300 hover:bg-primary/10 hover:text-primary'
          }`}
          onClick={() => onChangeCategory(c)}
        >
          {c}
        </button>
      ))}
    </div>
  )
}

export default CategoryChoice
