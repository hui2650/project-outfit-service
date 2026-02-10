// 레이아웃만 2컬럼 그리드

import React from "react";
import Header from "./Header";
import { useLayout } from "../../store/layoutStore";

const AppShell = ({ left, right }) => {
  const { panelCollapsed, setPanelCollapsed } = useLayout();
  return (
    <div className=" h-screen flex justify-between relative">
      {/* ✅ md 이하 + 패널 펼침 상태일 때 dim 배경 */}
      {!panelCollapsed && (
        <div
          className={[
            "fixed inset-0 z-20 bg-black/40 backdrop-blur-[0.5px]",
            "hidden max-lg:block", // ✅ 768px 포함해서 보여줌
          ].join(" ")}
          onClick={() => setPanelCollapsed(true)}
          aria-hidden="true"
        />
      )}
      {/* 메인 2패널 */}
      <div className="flex-1 flex flex-col overflow-hidden relative">
        {/* 좌측 (헤더+메인) */}
        <Header />
        {left}
      </div>
      {/* 우측 패널 */}
      <div className="h-full">{right}</div>
    </div>
  );
};

export default AppShell;
