import React from "react";
import AppShell from "../components/layout/AppShell";
import ResultStage from "../components/stage/ResultStage";
import SidePanel from "../components/panel/sidepanel/SidePanel.jsx";
import SessionPanel from "../components/panel/sidepanel/SessionPanel.jsx";

import { ChatPageProvider, useChatPage } from "./chat/ChatPageContext.jsx";

const HomeInner = () => {
  const {
    chatLogs,
    chatDisabled,
    handleSendChat,
    handleNewChat,
    rightPanelMode,
  } = useChatPage();

  return (
    <AppShell
      left={
        <ResultStage
          chatLogs={chatLogs}
          onSendChat={handleSendChat}
          chatDisabled={chatDisabled}
          onNewChat={handleNewChat}
        />
      }
      right={rightPanelMode === "input" ? <SidePanel /> : <SessionPanel />}
    />
  );
};

const Home = () => {
  return (
    <ChatPageProvider>
      <HomeInner />
    </ChatPageProvider>
  );
};

export default Home;
