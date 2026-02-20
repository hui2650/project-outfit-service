// src/pages/Hero.jsx
import React, { useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTransition } from '../store/transitionStore'
import { useAppData } from '../store/appDataStore'

import Header from '../components/layout/Header'

import usePagingSnap from '../hooks/usePagingSnap'
import HeroIntroFirst from '../components/hero/HeroIntroFirst'
import HeroIntroSecond from '../components/hero/HeroIntroSecond'

/*
Hero
- 랜딩(히어로) 페이지
- scroll container에 두 개의 섹션을 넣고 usePagingSnap으로 휠/스와이프 기반 스냅 이동을 구현
- 진입 시 resetGuest로 게스트 상태를 초기화(유저정보 플로우를 새로 시작)
*/
const Hero = () => {
  const nav = useNavigate()
  const { leaving, handleStart } = useTransition()
  const { resetGuest } = useAppData()

  const scrollerRef = useRef(null)

  React.useEffect(() => {
    resetGuest()
  }, [resetGuest])

  usePagingSnap(scrollerRef, {
    selector: '[data-hero-section]',
    lockMs: 900,
    wheelThreshold: 40,
    swipeThresholdPx: 60,
    durationMs: 650,
  })

  return (
    <div className="h-screen overflow-hidden">
      <Header />

      {/* 내부 스크롤 컨테이너: 스냅 이동 대상 */}
      <div ref={scrollerRef} className="h-full overflow-y-auto scroll-smooth">
        <div data-hero-section>
          <HeroIntroFirst
            leaving={leaving}
            handleStart={() => handleStart(() => nav('/user-info-nickname'))}
          />
        </div>

        <div data-hero-section>
          <HeroIntroSecond
            leaving={leaving}
            handleStart={() => handleStart(() => nav('/user-info-nickname'))}
          />
        </div>
      </div>
    </div>
  )
}

export default Hero
