import React from "react";

const TransitionContext = React.createContext(null);

export const TransitionProvider = ({ children }) => {
  const [leaving, setLeaving] = React.useState(false);

  // 공통 시작 함수: leaving true로 만들고, 필요하면 callback 실행
  const handleStart = React.useCallback(
    (next) => {
      if (leaving) return; // 중복 클릭 방지
      setLeaving(true);

      // 애니메이션 시간(예: 300ms) 이후 다음 행동 실행
      window.setTimeout(() => {
        next?.();
        setLeaving(false); // 다음 화면에서 계속 쓰려면 false로 복구
      }, 300);
    },
    [leaving],
  );

  return (
    <TransitionContext.Provider value={{ leaving, handleStart }}>
      {children}
    </TransitionContext.Provider>
  );
};

export const useTransition = () => {
  const ctx = React.useContext(TransitionContext);
  if (!ctx)
    throw new Error("useTransition must be used within TransitionProvider");
  return ctx;
};
