// src/store/layoutStore.jsx
import React from 'react'

const LayoutCtx = React.createContext(null)

/*
LayoutProvider
- 레이아웃 전용 UI 상태 저장소
- panelCollapsed: 우측 패널이 접힘 상태인지 여부
- panelCollapsed는 화면 크기/오버레이 동작과 연결되므로 전역 UI 상태로 두는 것이 편함
*/
export function LayoutProvider({ children }) {
  const [panelCollapsed, setPanelCollapsed] = React.useState(false)

  /*
  value
  - setPanelCollapsed까지 포함해서 패널 열기/닫기를 어디서든 제어 가능
  - useMemo로 참조 안정성 확보
  */
  const value = React.useMemo(
    () => ({ panelCollapsed, setPanelCollapsed }),
    [panelCollapsed]
  )

  return <LayoutCtx.Provider value={value}>{children}</LayoutCtx.Provider>
}

/*
useLayout
- Provider 범위를 강제해 잘못된 사용을 조기에 발견
*/
export function useLayout() {
  const v = React.useContext(LayoutCtx)
  if (!v) throw new Error('useLayout must be used within LayoutProvider')
  return v
}
