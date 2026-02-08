// 오른쪽 영역
// 업로드, 텍스트, 제출 버튼을 모아서 배치

import React from 'react'
import SidePanelRail from './SidePanelRail'
import SidePanelHeader from './SidePanelHeader'
import SidePanelContent from './SidePanelContent'
import SidePanelFooter from './SidePanelFooter'

const SidePanel = ({
  previewUrl,
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
  const [collapsed, setCollapsed] = React.useState(false)

  return (
    <aside
      className={[
        'relative h-full shrink-0 z-10 overflow-hidden',
        'bg-card/50 backdrop-blur-md',
        'transition-[width] duration-300 ease-in-out',
        collapsed ? 'w-[72px]' : 'w-[380px] max-w-sm',
      ].join(' ')}
    >
      {collapsed && (
        <SidePanelRail
          collapsed={collapsed}
          onToggle={() => setCollapsed(false)}
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
        <SidePanelHeader onCollapse={() => setCollapsed(true)} />
        <SidePanelContent
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
