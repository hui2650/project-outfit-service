import React from "react";

const MobileMenuButton = ({ onClick, ariaLabel = "메뉴 열기" }) => {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={ariaLabel}
      className="md:hidden h-10 w-10 rounded-xl border border-border bg-card/10 hover:bg-muted/40 active:scale-[0.98] transition flex items-center justify-center"
    >
      {/* 햄버거 아이콘 (SVG) */}
      <svg
        width="22"
        height="22"
        viewBox="0 0 24 24"
        fill="none"
        className="text-foreground"
        xmlns="http://www.w3.org/2000/svg"
      >
        <path
          d="M4 7H20"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
        />
        <path
          d="M4 12H20"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
        />
        <path
          d="M4 17H20"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
        />
      </svg>
    </button>
  );
};

export default MobileMenuButton;
