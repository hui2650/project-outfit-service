import React from 'react'
import UserButton from '../../common/UserButton'
import NewChatButton from '../../common/NewChatButton'
import HistoryChatListButton from '../../common/HistoryChatListButton'

const SidePanelRail = ({
  collapsed,
  onToggle,
  onOpenSessions,
  onOpenInput,
}) => {
  return (
    <div className="absolute right-0 top-0 h-full w-[72px] border-l border-border bg-card/80 flex flex-col items-center justify-between py-4">
      <div className="flex flex-col gap-4">
        {/*  패널 열기 버튼: 항상 input으로 */}
        <button
          type="button"
          onClick={() => {
            onOpenInput?.() //  먼저 모드 세팅
            onToggle() //  펼치기
          }}
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

        <NewChatButton />

        {/*  🕘: 펼치고 sessions로 */}
        <HistoryChatListButton
          onClick={() => {
            onOpenSessions?.() //  먼저 모드 세팅
            onToggle() //  펼치기
          }}
        />
      </div>

      <UserButton to="/userpage" confirmBeforeNav={false} />
    </div>
  )
}

export default SidePanelRail
