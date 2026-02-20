// src/pages/Home.jsx
import React from 'react'
import AppShell from '../components/layout/AppShell'
import ResultStage from '../components/stage/ResultStage'
import SidePanel from '../components/panel/sidepanel/SidePanel.jsx'
import SessionPanel from '../components/panel/sidepanel/SessionPanel.jsx'
import { useAppData } from '../store/appDataStore.jsx'

import { ChatPageProvider, useChatPage } from './chat/ChatPageContext.jsx'
import { Navigate } from 'react-router-dom'

/*
HomeInner
- ChatPageProvider 내부에서만 접근 가능한 상태(useChatPage)를 사용해
  메인 결과 영역(ResultStage)과 우측 패널(SidePanel/SessionPanel)을 조립
*/
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

/*
Home
- 닉네임이 없으면 유저정보 입력 페이지로 이동시켜
  채팅/추천 페이지에 진입하기 위한 최소 정보(닉네임)를 보장
- 닉네임이 있으면 ChatPageProvider로 감싸서 채팅 상태를 활성화
*/
const Home = () => {
  const { guest } = useAppData()
  const nick = (guest?.nickname ?? '').trim()

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
