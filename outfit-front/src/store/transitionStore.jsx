// src/store/transitionStore.jsx
import React from 'react'

const TransitionContext = React.createContext(null)

/*
TransitionProvider
- 페이지 전환 애니메이션(leave/out) 제어를 위한 전역 상태
- leaving: 전환 중 여부(중복 클릭 방지에도 사용)
- handleStart(next):
  1) leaving을 true로 세팅
  2) 일정 시간 후 next 실행(라우팅/상태 변경)
  3) leaving을 false로 되돌려 다음 전환 가능하게 함
*/
export const TransitionProvider = ({ children }) => {
  const [leaving, setLeaving] = React.useState(false)

  /*
  handleStart(next)
  - leaving이 이미 true면 무시하여 중복 전환을 차단
  - setTimeout 시간은 motion 애니메이션 duration과 일치시키는 것이 자연스럽다
  */
  const handleStart = React.useCallback(
    (next) => {
      if (leaving) return
      setLeaving(true)

      window.setTimeout(() => {
        next?.()
        setLeaving(false)
      }, 300)
    },
    [leaving]
  )

  return (
    <TransitionContext.Provider value={{ leaving, handleStart }}>
      {children}
    </TransitionContext.Provider>
  )
}

/*
useTransition
- Provider 범위를 강제해 잘못된 사용을 조기에 발견
*/
export const useTransition = () => {
  const ctx = React.useContext(TransitionContext)
  if (!ctx)
    throw new Error('useTransition must be used within TransitionProvider')
  return ctx
}
