// src/components/layout/AppShell.jsx
// 레이아웃만 2컬럼 구조(메인 영역 + 우측 패널)

import React from 'react'
import Header from './Header'
import { useLayout } from '../../store/layoutStore'

/*
AppShell
- 좌측 메인(채팅/결과) + 우측 패널(입력/세션)을 나란히 배치하는 레이아웃 컨테이너
- 모바일/태블릿(max-lg)에서 패널이 펼쳐졌을 때 dim overlay를 올려서
  우측 fixed 패널이 "모달처럼" 느껴지게 하고, 바깥 클릭 시 접힘 처리
*/
const AppShell = ({ left, right }) => {
  const { panelCollapsed, setPanelCollapsed } = useLayout()

  return (
    <div className="h-screen flex justify-between relative mx-auto shadow">
      {/* 모바일/태블릿에서 패널이 열린 상태면 배경을 어둡게 처리하고 클릭으로 접기 */}
      {!panelCollapsed && (
        <div
          className={[
            'fixed inset-0 z-20 bg-black/40 backdrop-blur-[0.5px]',
            'hidden max-lg:block',
          ].join(' ')}
          onClick={() => setPanelCollapsed(true)}
          aria-hidden="true"
        />
      )}

      {/* 좌측 메인 영역: 헤더 + left 콘텐츠(채팅/결과) */}
      <div className="flex-1 flex flex-col overflow-hidden relative">
        <Header />
        {left}
      </div>

      {/* 우측 영역: right 콘텐츠(입력 패널/세션 패널) */}
      <div className="h-full">{right}</div>
    </div>
  )
}

export default AppShell
