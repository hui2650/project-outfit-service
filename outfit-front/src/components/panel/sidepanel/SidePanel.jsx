import React from 'react'
import PanelShell from '../../layout/PanelShell'
import SidePanelHeader from './SidePanelHeader'
import SidePanelContent from './SidePanelContent'
import SidePanelFooter from './SidePanelFooter'
import { useLayout } from '../../../store/layoutStore'
import { useChatPage } from '../../../pages/chat/ChatPageContext.jsx' // 경로 맞춰

/*
SidePanel
- 아이템 입력(업로드/성별/카테고리/텍스트쿼리) 패널
- PanelShell을 사용해 rail/header/footer 슬롯으로 조립
- header의 토글 버튼으로 SessionPanel(이전 채팅) 모드로 전환
*/

const SidePanel = () => {
  const { setPanelCollapsed } = useLayout()
  const { openSessionsPanel, openInputPanel } = useChatPage()

  return (
    <PanelShell
      /*
      rail
      - collapsed 상태에서 표시되는 SidePanelRail에 전달할 핸들러
      - rail에서 "이전 채팅" / "아이템 입력" 모드 전환을 수행
      */
      rail={{ onOpenSessions: openSessionsPanel, onOpenInput: openInputPanel }}
      header={
        <SidePanelHeader
          // 헤더 우측 버튼: 패널 접기(rail로 전환)
          onCollapse={() => setPanelCollapsed(true)}
          title="아이템 입력"
          // 모드 토글 버튼: 세션 패널로 이동
          onToggleMode={openSessionsPanel}
          isSessionMode={false}
        />
      }
      footer={<SidePanelFooter />}
    >
      {/* 실제 입력 UI: 업로드/옵션/제출 */}
      <SidePanelContent loading={false} />
    </PanelShell>
  )
}

export default SidePanel
