import React from "react";

import { useNavigate, useLocation } from "react-router-dom";
import { useAppData } from "../../store/appDataStore";
import ConfirmModal from "./ConfirmModal";
import { useLayout } from "../../store/layoutStore";

const UserButton = ({ to = "/userpage", confirmBeforeNav = true }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const { guest } = useAppData();
  const nickname = guest?.nickname?.trim() || "히스토리";

  const [open, setOpen] = React.useState(false);
  const { panelCollapsed } = useLayout();

  const go = () => navigate(to);

  const onClick = () => {
    if (location.pathname === to) return;
    if (!confirmBeforeNav) return go();
    setOpen(true);
  };

  return (
    <>
      <div className="flex items-center gap-2.5">
        <button
          type="button"
          onClick={onClick}
          className="h-9 w-9 rounded-full bg-primary/20 flex items-center justify-center"
          aria-label="User"
          title="게스트 사용자"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="text-primary"
            aria-hidden="true"
          >
            <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"></path>
            <circle cx="12" cy="7" r="4"></circle>
          </svg>
        </button>
        {!panelCollapsed && (
          <h2 className="text-md truncate max-w-[120px]">{nickname}님</h2>
        )}
      </div>
      <ConfirmModal
        open={open}
        onClose={() => setOpen(false)}
        title="사용자 탭으로 이동"
        message="좋아요/히스토리 페이지로 이동할까요?"
        confirmText="이동"
        cancelText="취소"
        onConfirm={go}
        bgColor={"bg-primary/80"}
      />
    </>
  );
};

export default UserButton;
