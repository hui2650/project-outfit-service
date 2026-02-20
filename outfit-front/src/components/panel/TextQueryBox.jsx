/*
TextQueryBox
- 텍스트 조건 입력(색/아이템명/스타일 등)을 위한 textarea
- 입력값은 ChatPageContext의 textQuery로 관리되며 submit 시 서버로 전달
*/

const TextQueryBox = ({ textQuery, onTextQuery }) => {
  return (
    <div className="mt-8">
      <textarea
        className="w-full h-32 rounded-xl p-3 text-sm outline-none resize-none
        bg-background border border-border
        focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring
        focus-visible:ring-offset-2 focus-visible:ring-offset-background
        placeholder:text-muted-foreground"
        placeholder='(예: "베이지 싱글코트")'
        value={textQuery}
        onChange={(e) => onTextQuery(e.target.value)}
      />
    </div>
  )
}

export default TextQueryBox
