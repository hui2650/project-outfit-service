// src/components/layout/Header.jsx
import React from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import DarkModeToggle from '../common/DarkModeToggle'
import { useChatPage } from '../../pages/chat/ChatPageContext'
import MobileMenuButton from '../common/MobileMenuButton'
import { useLayout } from '../../store/layoutStore'

/*
Header
- 전역 상단 바
- 페이지 경로에 따라 로고 클릭 동작과 스타일이 달라짐
  - 유저정보 입력 페이지: 새로고침(입력 상태를 해당 페이지에서 초기화)
  - 채팅 페이지: 새 채팅 시작(세션/로그 초기화 목적)
  - 그 외: /chat으로 이동
- ChatPageProvider 밖에서 렌더될 수 있어 useChatPage 접근은 try/catch로 방어
*/

const USER_INFO_PATHS = new Set([
  '/',
  '/user-info-style',
  '/user-info-nickname',
])

const Header = () => {
  const location = useLocation()
  const navigate = useNavigate()
  const { setPanelCollapsed } = useLayout()
  const [mobileMenuOpen, setMobileMenuOpen] = React.useState(false)

  const pathname = location.pathname
  const isHeroPage = pathname === '/'
  const isChatPage = pathname === '/chat'
  const isUserInfoPage = USER_INFO_PATHS.has(pathname)

  const openMobileMenu = () => setMobileMenuOpen(true)
  const closeMobileMenu = () => setMobileMenuOpen(false)

  // ChatPageProvider 밖에서 Header가 렌더될 수 있으므로 안전하게 접근
  let chatApi = null
  try {
    chatApi = useChatPage()
  } catch {}

  /*
  로고 클릭 정책
  - 유저정보 입력 흐름에서는 새로고침으로 상태를 다시 시작
  - 채팅 화면에서는 새 채팅으로 세션을 리셋
  - 그 외에는 /chat으로 이동
  */
  const handleLogoClick = (e) => {
    if (isUserInfoPage) {
      e.preventDefault()
      navigate(0)
      return
    }

    if (isChatPage) {
      e.preventDefault()
      chatApi?.handleNewChat?.()
      return
    }

    e.preventDefault()
    navigate('/chat')
  }

  return (
    <header
      className={[
        'left-0 top-0 w-full h-14',
        'px-4 sm:px-6 lg:px-8',
        // 채팅 페이지가 아닐 때는 상단 고정(히어로/유저정보 페이지에서 배경 위에 올림)
        !isChatPage ? 'fixed z-50' : '',
        // 히어로 페이지가 아닐 때만 헤더 배경을 불투명하게(스크롤 시 가독성)
        !isHeroPage ? 'bg-background' : '',
      ].join(' ')}
    >
      <div
        className={[
          'w-full h-14 flex items-center justify-between',
          // 히어로 페이지에서는 border를 빼서 더 가벼운 느낌
          !isHeroPage ? 'border-b border-border' : '',
        ].join(' ')}
      >
        <a
          id="logo"
          href="/"
          onClick={handleLogoClick}
          className="text-lg md:text-xl text-foreground font-semibold"
        >
          Outfit Service
        </a>

        <div className="flex items-center gap-2">
          <DarkModeToggle />
          <MobileMenuButton
            onClick={() => {
              /*
              모바일 햄버거 동작
              - 채팅 페이지: 우측 입력 패널을 열고(panelCollapsed=false) 입력 모드로 전환
              - 그 외: 별도의 모바일 메뉴를 여는 확장 포인트
              */
              if (isChatPage) {
                chatApi?.openInputPanel?.()
                setPanelCollapsed?.(false)
                return
              }
              openMobileMenu()
            }}
          />
        </div>
      </div>
    </header>
  )
}

export default Header
