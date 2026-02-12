import React from 'react'
import SidePanelRail from '../panel/sidepanel/SidePanelRail'
import { useLayout } from '../../store/layoutStore'

const PanelShell = ({ rail, header, children, footer }) => {
  const { panelCollapsed: collapsed, setPanelCollapsed } = useLayout()

  return (
    <aside
      className={[
        'h-full shrink-0 z-30 overflow-hidde',
        collapsed
          ? 'relative w-[72px]'
          : 'fixed right-0 top-0 h-full w-[380px]',
        'lg:relative lg:h-full',
        collapsed ? 'lg:w-[72px]' : 'lg:w-[380px]',
      ].join(' ')}
    >
      {collapsed && (
        <SidePanelRail
          collapsed={collapsed}
          onToggle={() => setPanelCollapsed(false)}
          {...rail}
        />
      )}

      <div
        className={[
          'relative bg-card border-l border-border flex flex-col h-full',
          collapsed ? 'pr-[72px]' : 'pr-0',
          'ss duration-200',
          collapsed
            ? 'opacity-0 pointer-events-none translate-x-2'
            : 'opacity-100 translate-x-0',
        ].join(' ')}
      >
        {header}
        <div className="flex-1 overflow-y-auto">{children}</div>
        {footer}
      </div>
    </aside>
  )
}

export default PanelShell
