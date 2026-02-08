import React from 'react'
import DarkModeToggle from '../DarkModeToggle'

const SidePanelFooter = () => {
  return (
    <div className="p-6 w-full flex justify-between bg-card/80 shrink-0 border-t ">
      <div className="flex items-center gap-2">
        <button
          type="button"
          className="h-10 w-10 rounded-full bg-primary/20 flex items-center justify-center"
          aria-label="User"
          title="게스트 사용자"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="text-primary"
            aria-hidden="true"
          >
            <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"></path>
            <circle cx="12" cy="7" r="4"></circle>
          </svg>
        </button>
        <div>
          <h2 className="text-sm">게스트 사용자</h2>
          <span className="text-xs">로그인하여 저장하기</span>
        </div>
      </div>
      <DarkModeToggle />
    </div>
  )
}

export default SidePanelFooter
