import React from 'react'

const GenderChoice = ({ gender, onChangeGender }) => {
  const genders = ['man', 'woman']

  return (
    <div className="flex gap-2 mt-8 mb-4 flex-wrap">
      {genders.map((g) => (
        <button
          key={g}
          type="button"
          className={`px-3 py-1.5 rounded-full border transition-colors duration-150 ${
            gender === g
              ? 'bg-primary text-white'
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
