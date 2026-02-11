import React from 'react'
import SidePanelHeader from '../sidepanel/SidePanelHeader'
import SidePanelFooter from '../sidepanel/SidePanelFooter'
import PanelShell from '../../layout/PanelShell.jsx'
import { useLayout } from '../../../store/layoutStore.jsx'
import { useAppData } from '../../../store/appDataStore.jsx'
import { useChatPage } from '../../../pages/chat/ChatPageContext.jsx' // 경로 맞춰

const SessionPanel = () => {
  const { chatSessions, currentSessionId, setCurrentSessionId } = useAppData()
  const { setPanelCollapsed } = useLayout()
  const { openInputPanel, openSessionsPanel } = useChatPage()

  return (
    <PanelShell
      rail={{ onOpenInput: openInputPanel, onOpenSessions: openSessionsPanel }}
      header={
        <SidePanelHeader
          title="이전 채팅"
          onCollapse={() => setPanelCollapsed(true)}
          onToggleMode={openInputPanel}
          isSessionMode={true}
        />
      }
      footer={<SidePanelFooter />}
    >
      <div className="p-4 space-y-2">
        {chatSessions.map((s) => {
          const active = s.sessionId === currentSessionId
          return (
            <button
              key={s.sessionId}
              type="button"
              onClick={() => {
                setCurrentSessionId(s.sessionId)
                openInputPanel() //  선택 후 input으로 돌아가고 싶으면
              }}
              className={[
                'w-full text-left rounded-xl border p-3 transition',
                active ? 'bg-accent/40' : 'hover:bg-accent/20',
              ].join(' ')}
            >
              <div className="font-semibold text-sm">
                {s.title ?? '새 채팅'}
              </div>
              <div className="text-xs text-muted-foreground mt-1">
                {new Date(s.createdAt).toLocaleString()} ·{' '}
                {(s.turns ?? []).length} turns
              </div>
            </button>
          )
        })}
      </div>
    </PanelShell>
  )
}

export default SessionPanel
