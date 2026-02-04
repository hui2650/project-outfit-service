// 레이아웃만 2컬럼 그리드

import React from "react";

const AppShell = ({ left, right }) => {
  return (
    //  = 헤더 제외한 높이 고정
    <div className="w-full h-[calc(100vh-56px)] flex justify-between mx-auto bg-purple-50 shadow">
      {/* 메인 2패널 */}
      <div className="w-full overflow-hidden">{left}</div>
      <div className="min-w-72 bg-white">{right}</div>
    </div>
  );
};

export default AppShell;
