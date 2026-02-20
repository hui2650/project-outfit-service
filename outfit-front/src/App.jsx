import { BrowserRouter, Routes, Route } from 'react-router-dom'

import './App.css'
import Home from './pages/Home'
import Hero from './pages/Hero'
import UserPage from './pages/UserPage'

// 전역 상태/레이아웃/전환 상태 Provider
import { AppDataProvider } from './store/appDataStore.jsx'
import { LayoutProvider } from './store/layoutStore.jsx'
import { TransitionProvider } from './store/transitionStore.jsx'

// 유저정보 입력 플로우 페이지
import UserPageNickName from './pages/UserPageNickName.jsx'
import UserPageStyle from './pages/UserPageStyle.jsx'

/**
 * App()
 *
 * 역할
 * - Provider 트리를 최상단에 배치하여 어디서든 useAppData/useLayout/useTransition 사용 가능하게 함
 * - 라우팅 테이블 정의
 *
 * Provider 순서 의미
 * - AppDataProvider: 사용자 데이터/세션/채팅/좋아요/히스토리 (앱의 핵심 데이터)
 * - LayoutProvider: 패널 접힘 상태(panelCollapsed) 같은 UI 레이아웃 상태
 * - TransitionProvider: 화면 전환 애니메이션 상태(leaving)
 *
 * Router는 Provider들 안쪽에 두어도 되고 밖에 둬도 되지만,
 * 이 구조는 "페이지 컴포넌트들이 Provider 상태에 의존"하므로 안쪽에 두는 편이 자연스럽다.
 */
function App() {
  return (
    <AppDataProvider>
      <LayoutProvider>
        <TransitionProvider>
          <BrowserRouter>
            <Routes>
              {/* Hero(랜딩) */}
              <Route path="/" element={<Hero />} />

              {/* 메인 채팅/추천 화면 */}
              <Route path="/chat" element={<Home />} />

              {/* 유저 정보 입력 단계 1: 닉네임 */}
              <Route
                path="/user-info-nickname"
                element={<UserPageNickName />}
              />

              {/* 유저 정보 입력 단계 2: 스타일 */}
              {/* 여기 path는 반드시 "/user-info-style"이어야 함 */}
              <Route path="/user-info-style" element={<UserPageStyle />} />

              {/* 유저 페이지(좋아요/히스토리) */}
              <Route path="/userpage" element={<UserPage />} />
            </Routes>
          </BrowserRouter>
        </TransitionProvider>
      </LayoutProvider>
    </AppDataProvider>
  )
}

export default App
