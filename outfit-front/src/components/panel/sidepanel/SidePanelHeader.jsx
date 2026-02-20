import React from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faImage } from '@fortawesome/free-solid-svg-icons'

/*
SidePanelHeader
- 패널 상단 타이틀/모드 전환/접기 버튼 영역
- isSessionMode 값에 따라 토글 버튼 텍스트가 바뀜
- onToggleMode는 "입력 패널 ↔ 이전 채팅 패널" 전환에 사용
*/

const SidePanelHeader = ({
  onCollapse,
  title,
  onToggleMode,
  isSessionMode,
}) => {
  return (
    <div className="p-4 shrink-0 border-b flex justify-between items-center bg-card/80">
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-3">
          <FontAwesomeIcon
            icon={faImage}
            className="text-base px-1 py-1.5 rounded-[9px] md:text-lg md:px-1.5 md:py-2 md:rounded-xl 
             text-primary/80 bg-primary/15"
          />
          <h2 className="text-sm md:text-base font-foreground font-semibold leading-loose">
            {title}
          </h2>
        </div>

        {/* 🔁 토글 버튼: 입력 패널과 세션 패널 사이 이동 */}
        <button
          type="button"
          onClick={onToggleMode}
          className="text-xs px-2 py-1 rounded-md border border-border hover:bg-muted/80"
        >
          {isSessionMode ? '아이템 입력' : '이전 채팅'}
        </button>
      </div>
      {/* 패널 접기 버튼: collapsed 상태로 전환 */}
      <button
        type="button"
        onClick={onCollapse}
        className="h-9 w-9 rounded-xl border border-border bg-card hover:bg-muted flex items-center justify-center"
        aria-label="Collapse side panel"
        title="접기"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="24"
          height="24"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="lucide lucide-panel-right-close h-5 w-5 text-forground/80"
          aria-hidden="true"
        >
          <rect width="18" height="18" x="3" y="3" rx="2"></rect>
          <path d="M15 3v18"></path>
          <path d="m8 9 3 3-3 3"></path>
        </svg>
      </button>
    </div>
  )
}

export default SidePanelHeader
