import React from 'react'

const TextQueryBox = ({ textQuery, onTextQuery }) => {
  return (
    <div className="mt-8">
      <textarea
<<<<<<< HEAD
        className="w-full h-32 border rounded-xl p-3 text-sm outline-none focus:ring-2 focus:ring-violet-200 resize-none whitespace-pre-line"
=======
        className=" w-full h-32 rounded-xl p-3 text-sm outline-none resize-none
        bg-background border border-border
        focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring
        focus-visible:ring-offset-2 focus-visible:ring-offset-background
        placeholder:text-muted-foreground"
>>>>>>> feature/taehui/default-uI
        placeholder='(예: "베이지 싱글코트")'
        value={textQuery}
        onChange={(e) => onTextQuery(e.target.value)}
      ></textarea>
    </div>
  )
}

export default TextQueryBox
