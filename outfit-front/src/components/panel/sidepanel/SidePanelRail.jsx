import React from 'react'

const SidePanelRail = ({ collapsed, onToggle }) => {
  return (
    <div className="absolute right-0 top-0 h-full w-[72px] border-l border-border bg-card/80 flex flex-col items-center justify-between py-4">
      {/* 위: 패널 열기/닫기 */}
      <button
        type="button"
        onClick={onToggle}
        className="h-10 w-10 rounded-xl border border-border bg-card hover:bg-muted flex items-center justify-center"
        aria-label={collapsed ? 'Open side panel' : 'Collapse side panel'}
        title={collapsed ? '열기' : '접기'}
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
          className="lucide lucide-panel-right h-5 w-5"
          aria-hidden="true"
        >
          <rect width="18" height="18" x="3" y="3" rx="2"></rect>
          <path d="M15 3v18"></path>
        </svg>
      </button>

      {/* 사용자 */}
      <button
        type="button"
        className="h-10 w-10 rounded-full bg-primary/20 flex items-center justify-center"
        aria-label="User"
        title="게스트 사용자"
      >
        {/* lucide-user 그대로 쓰고 싶으면 지금 svg 넣어도 됨 */}
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
    </div>
  )
}

export default SidePanelRail
