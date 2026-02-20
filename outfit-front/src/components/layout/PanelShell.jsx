import React from 'react'
import SidePanelRail from '../panel/sidepanel/SidePanelRail'
import { useLayout } from '../../store/layoutStore'

/*
PanelShell
- 오른쪽 패널의 공통 레이아웃 프레임
- collapsed 상태에서는 md 이상에서만 rail(62px)을 보여주고, 모바일에서는 rail 공간을 아예 만들지 않음
- header / children / footer를 슬롯처럼 받아서 SidePanel(입력)과 SessionPanel(이전채팅)이 같은 껍데기를 공유
*/

const PanelShell = ({ rail, header, children, footer }) => {
  const { panelCollapsed: collapsed, setPanelCollapsed } = useLayout()

  /*
  showRail
  - rail은 collapsed일 때만 렌더
  - hidden md:block로 모바일에서는 rail 자체가 렌더되지 않도록 제거
  */
  const showRail = collapsed // rail 자체는 collapsed일 때만 렌더

  /*
  railOffsetClass
  - rail(62px)을 오른쪽에 붙여두고 본문 컨텐츠가 겹치지 않도록 md 이상에서 padding-right 확보
  - 모바일에서는 rail 개념이 없으므로 pr-0 유지
  */
  const railOffsetClass = collapsed ? 'md:pr-[62px] pr-0' : 'pr-0'

  return (
    <aside
      className={[
        'h-full shrink-0 z-30 overflow-hidden',

        /*
        너비/포지션 정책
        - collapsed: 모바일에서는 w-0으로 공간 자체를 제거, md 이상에서만 rail 폭(62px)
        - expanded: 모바일/태블릿에서는 fixed로 우측 오버레이 패널, 데스크톱(lg)부터는 relative로 레이아웃 패널
        */
        collapsed
          ? 'relative w-0 md:w-[62px]'
          : ': fixed right-0 top-0 h-full w-[320px] md:w-[380px]',

        /*
        lg 브레이크포인트 정책
        - 큰 화면에서는 fixed 오버레이가 아니라, 좌/우 레이아웃의 일부로 고정
        */
        'lg:relative lg:h-full',
        collapsed ? 'lg:w-[62px]' : 'lg:w-[380px]',
      ].join(' ')}
    >
      {/*  rail은 md 이상에서만 보이게 (모바일에서 공간/클릭영역 제거) */}
      {showRail && (
        <div className="hidden md:block">
          <SidePanelRail
            collapsed={collapsed}
            onToggle={() => setPanelCollapsed(false)}
            {...rail}
          />
        </div>
      )}

      <div
        className={[
          /*
          패널 본문 컨테이너
          - bg-card + border-l로 오른쪽 패널 경계 형성
          - flex-col로 header / content / footer를 수직 배치
          */
          'relative bg-card border-l border-border flex flex-col h-full',

          // rail이 있을 때 md 이상에서만 우측 padding 확보
          railOffsetClass,

          // 토글 애니메이션(빠른 전환)
          'duration-200',
          collapsed
            ? 'opacity-0 pointer-events-none translate-x-2'
            : 'opacity-100 translate-x-0',
        ].join(' ')}
      >
        {header}
        {/* children 영역은 내부에서 스크롤을 만들 수 있도록 overflow-hidden */}
        <div className="flex-1 overflow-hidden">{children}</div>
        {footer}
      </div>
    </aside>
  )
}

export default PanelShell
