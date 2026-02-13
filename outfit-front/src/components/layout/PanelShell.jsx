import React from "react";
import SidePanelRail from "../panel/sidepanel/SidePanelRail";
import { useLayout } from "../../store/layoutStore";

const PanelShell = ({ rail, header, children, footer }) => {
  const { panelCollapsed: collapsed, setPanelCollapsed } = useLayout();

  //  모바일에서는 rail/62px 예약 자체를 없애고
  //  md 이상에서만 collapsed 상태(62px rail) 지원
  const showRail = collapsed; // rail 자체는 collapsed일 때만 렌더
  const railOffsetClass = collapsed ? "md:pr-[62px] pr-0" : "pr-0";

  return (
    <aside
      className={[
        "h-full shrink-0 z-30 overflow-hidden",

        //  모바일: 패널은 고정 패널(열렸을 때만 의미), 접힘(rail) 개념은 md부터
        // collapsed일 때 모바일에서 62px 박스 만들지 않기
        collapsed
          ? "relative w-0 md:w-[62px]"
          : ": fixed right-0 top-0 h-full w-[320px] md:w-[380px]",

        //  lg에서는 원래 정책 유지
        "lg:relative lg:h-full",
        collapsed ? "lg:w-[62px]" : "lg:w-[380px]",
      ].join(" ")}
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
          "relative bg-card border-l border-border flex flex-col h-full",

          //  rail 폭 예약은 md 이상에서만
          railOffsetClass,

          "duration-200",
          collapsed
            ? "opacity-0 pointer-events-none translate-x-2"
            : "opacity-100 translate-x-0",
        ].join(" ")}
      >
        {header}
        <div className="flex-1 overflow-hidden">{children}</div>
        {footer}
      </div>
    </aside>
  );
};

export default PanelShell;
