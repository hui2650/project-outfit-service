// 오른쪽 영역
// 업로드, 텍스트, 제출 버튼을 모아서 배치

import React from 'react'
import SidePanelRail from './SidePanelRail'
import SidePanelHeader from './SidePanelHeader'
import SidePanelContent from './SidePanelContent'
import SidePanelFooter from './SidePanelFooter'
import { useLayout } from '../../../store/layoutStore'

const SidePanel = ({
  previewUrl,
  inputRef,
  textQuery,
  onTextQuery,
  onFile,
  onSubmit,
  loading,
  onChangeCategory,
  category,
  gender,
  onChangeGender,
  file,
  error,
}) => {
  const { panelCollapsed: collapsed, setPanelCollapsed } = useLayout()

  return (
    <aside
      className={[
        'h-full shrink-0 z-30 overflow-hidden bg-card/90',
        // 📱 모바일 기본 (md 미만)
        collapsed
          ? 'relative w-[72px]'
          : 'fixed right-0 top-0 h-full w-[380px]',
        // 💻 md 이상에서 정상 레이아웃 복구
        'lg:relative lg:h-full',
        collapsed ? 'lg:w-[72px]' : 'lg:w-[380px]',
      ].join(' ')}
    >
      {collapsed && (
        <SidePanelRail
          collapsed={collapsed}
          onToggle={() => setPanelCollapsed(false)}
        />
      )}

      <div
        className={[
          'relative bg-card/50 backdrop-blur-md border-l border-border flex flex-col h-full',
          collapsed ? 'pr-[72px]' : 'pr-0',
          'transition-[opacity,transform] duration-200',
          collapsed
            ? 'opacity-0 pointer-events-none translate-x-2'
            : 'opacity-100 translate-x-0',
        ].join(' ')}
      >
        <SidePanelHeader onCollapse={() => setPanelCollapsed(true)} />
        <SidePanelContent
          inputRef={inputRef}
          previewUrl={previewUrl}
          textQuery={textQuery}
          onTextQuery={onTextQuery}
          onFile={onFile}
          onSubmit={onSubmit}
          loading={loading}
          onChangeCategory={onChangeCategory}
          category={category}
          gender={gender}
          onChangeGender={onChangeGender}
          file={file}
          error={error}
        />
        <SidePanelFooter />
      </div>
    </aside>
  )
}

export default SidePanel
