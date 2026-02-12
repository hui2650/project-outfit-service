import React from "react";
import PanelShell from "../../layout/PanelShell";
import SidePanelHeader from "./SidePanelHeader";
import SidePanelContent from "./SidePanelContent";
import SidePanelFooter from "./SidePanelFooter";
import { useLayout } from "../../../store/layoutStore";
import { useChatPage } from "../../../pages/chat/ChatPageContext.jsx"; // 경로 맞춰

const SidePanel = () => {
  const { setPanelCollapsed } = useLayout();
  const { openSessionsPanel, openInputPanel } = useChatPage();

  return (
    <PanelShell
      rail={{ onOpenSessions: openSessionsPanel, onOpenInput: openInputPanel }}
      header={
        <SidePanelHeader
          onCollapse={() => setPanelCollapsed(true)}
          title="아이템 입력"
          onToggleMode={openSessionsPanel}
          isSessionMode={false}
        />
      }
      footer={<SidePanelFooter />}
    >
      <SidePanelContent loading={false} />
    </PanelShell>
  );
};

export default SidePanel;
