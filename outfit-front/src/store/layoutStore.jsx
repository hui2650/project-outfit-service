import React from "react";

const LayoutCtx = React.createContext(null);

export function LayoutProvider({ children }) {
  const [panelCollapsed, setPanelCollapsed] = React.useState(false);

  const value = React.useMemo(
    () => ({ panelCollapsed, setPanelCollapsed }),
    [panelCollapsed],
  );

  return <LayoutCtx.Provider value={value}>{children}</LayoutCtx.Provider>;
}

export function useLayout() {
  const v = React.useContext(LayoutCtx);
  if (!v) throw new Error("useLayout must be used within LayoutProvider");
  return v;
}
