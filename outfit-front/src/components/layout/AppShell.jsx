// 레이아웃만 2컬럼 그리드

import React from 'react'

const AppShell = ({ left, right }) => {
  return (
    <div className=" h-screen flex justify-between relative mx-auto shadow">
      {/* 메인 2패널 */}
      <div className="flex-1 flex justify-center items-center overflow-hidden relative">
        {left}
      </div>
      <div className="h-full">{right}</div>
    </div>
  )
}

export default AppShell
