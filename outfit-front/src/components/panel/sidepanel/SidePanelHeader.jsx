import React from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faImage } from '@fortawesome/free-solid-svg-icons'

const SidePanelHeader = ({ onCollapse }) => {
  return (
    <div className="p-5 shrink-0 border-b flex justify-between bg-card/80">
      <div className="flex itmes-center gap-2">
        <FontAwesomeIcon
          icon={faImage}
          className="text-lg px-1.5 py-2 rounded-xl 
             text-primary bg-primary/15"
        />
        <h2 className="font-foreground font-semibold text-base leading-loose">
          아이템 입력
        </h2>
      </div>
      {/* 접는 버튼(헤더 우측) */}

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
          className="lucide lucide-panel-right-close h-5 w-5"
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
