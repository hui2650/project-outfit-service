import React from 'react'
import AppShell from '../components/layout/AppShell'
import ResultStage from '../components/stage/ResultStage'
import SidePanel from '../components/panel/sidepanel/SidePanel.jsx'
import SessionPanel from '../components/panel/sidepanel/SessionPanel.jsx'
import { useAppData } from '../store/appDataStore.jsx'

import { ChatPageProvider, useChatPage } from './chat/ChatPageContext.jsx'
import { Navigate } from 'react-router-dom'

const HomeInner = () => {
  const {
    chatLogs,
    chatDisabled,
    handleSendChat,
    handleNewChat,
    rightPanelMode,
  } = useChatPage()

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
      right={rightPanelMode === 'input' ? <SidePanel /> : <SessionPanel />}
    />
  )
}

const Home = () => {
  const { guest } = useAppData() // 추가
  const nick = (guest?.nickname ?? '').trim()

  // 닉네임 없으면 유저정보 입력 페이지로 강제 이동
  if (!nick) {
    return <Navigate to="/user-info-nickname" replace />
  }

  return (
    <ChatPageProvider>
      <HomeInner />
    </ChatPageProvider>
  )
}

export default Home
