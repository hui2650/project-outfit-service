import React from 'react'
import UserButton from '../../common/UserButton'

/*
SidePanelFooter
- 패널 하단 고정 영역
- UserPage 이동 버튼을 제공하며, 이동 전에 확인 모달을 띄우는 옵션 사용
*/

const SidePanelFooter = () => {
  return (
    <div className="p-4 w-full flex justify-between bg-card/80 shrink-0 border-t">
      <UserButton to="/userpage" confirmBeforeNav={true} />
    </div>
  )
}

export default SidePanelFooter
