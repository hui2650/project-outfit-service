import React from "react";

import { useNavigate, useLocation } from "react-router-dom";
import ConfirmModal from "./ConfirmModal";

const UserButton = ({ to = "/user", confirmBeforeNav = true }) => {
  const navigate = useNavigate();
  const location = useLocation();

  const [open, setOpen] = React.useState(false);

  const go = () => navigate(to);

  const onClick = () => {
    if (location.pathname === to) return;
    if (!confirmBeforeNav) return go();
    setOpen(true);
  };

  return (
    <>
      <button
        type="button"
        onClick={onClick}
        className="h-10 w-10 rounded-full bg-primary/20 flex items-center justify-center"
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
      <ConfirmModal
        open={open}
        onClose={() => setOpen(false)}
        title="사용자 탭으로 이동"
        message="좋아요/히스토리를 확인할 수 있어. 지금 이동할까?"
        confirmText="이동"
        cancelText="그냥 둘래"
        onConfirm={go}
      />
    </>
  );
};

export default UserButton;
