import React from 'react'

const CategoryChoice = ({ category, onChangeCategory }) => {
  const categories = [
<<<<<<< HEAD
    "top",
    "bottom",
    "skirt",
    "dress",
    "outer",
    "shoes",
    "bag",
  ];

  return (
    <div className="flex gap-2 mt-8 flex-wrap">
      {categories.map((c) => (
        <button
          key={c}
          type="button"
          className={`px-3 py-1.5 rounded-full border transition-colors duration-150 ${
            category === c
              ? "bg-primary text-white"
              : "bg-white text-gray-500 border-gray-300 hover:bg-primary/10 hover:text-primary"
          }`}
          onClick={() => onChangeCategory(c)}
        >
          {c}
        </button>
      ))}
    </div>
  );
};
=======
    'top',
    'bottom',
    'skirt',
    'dress',
    'outer',
    'shoes',
    'bag',
  ]
>>>>>>> feature/taehui/default-uI

  return (
    <div className="flex gap-2 mt-4 flex-wrap">
      {categories.map((c) => (
        <button
          key={c}
          type="button"
          className={`px-3 py-1.5 rounded-full border transition-colors duration-150 ${
            category === c
              ? 'bg-primary text-white'
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
