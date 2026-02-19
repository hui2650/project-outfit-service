import React from "react";
import UserButton from "../../common/UserButton";

const SidePanelFooter = () => {
  return (
    <div className="p-4 w-full flex justify-between bg-card/80 shrink-0 border-t">
      <UserButton to="/userpage" confirmBeforeNav={true} />
    </div>
  );
};

export default SidePanelFooter;
