import React from 'react'
import UserButton from '../../common/UserButton'

const SidePanelFooter = () => {
  return (
    <div className="p-6 w-full flex justify-between bg-card/80 shrink-0 border-t">
      <div className="flex items-center gap-2">
        <UserButton to="/userpage" confirmBeforeNav={false} />
        <div>
          <h2 className="text-sm">게스트 사용자</h2>
          <span className="text-xs">로그인하여 저장하기</span>
        </div>
      </div>
    </div>
  )
}

export default SidePanelFooter
