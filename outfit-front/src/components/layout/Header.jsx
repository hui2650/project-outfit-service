// src/components/layout/Header.jsx
import React from "react";
import { useLocation, useNavigate } from "react-router-dom";
import DarkModeToggle from "../common/DarkModeToggle";
import { useChatPage } from "../../pages/chat/ChatPageContext";
import MobileMenuButton from "../common/MobileMenuButton";
import { useLayout } from "../../store/layoutStore";

const USER_INFO_PATHS = new Set([
  "/",
  "/user-info-style",
  "/user-info-nickname",
]);

const Header = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { setPanelCollapsed } = useLayout();
  const [mobileMenuOpen, setMobileMenuOpen] = React.useState(false);

  const pathname = location.pathname;
  const isHeroPage = pathname === "/";
  const isChatPage = pathname === "/chat";
  const isUserInfoPage = USER_INFO_PATHS.has(pathname);

  const openMobileMenu = () => setMobileMenuOpen(true);
  const closeMobileMenu = () => setMobileMenuOpen(false);

  // ChatPageProvider 밖에서 Header가 렌더될 수 있으니 안전하게 try
  let chatApi = null;
  try {
    chatApi = useChatPage();
  } catch {}

  const handleLogoClick = (e) => {
    if (isUserInfoPage) {
      e.preventDefault();
      navigate(0);
      return;
    }

    if (isChatPage) {
      e.preventDefault();
      chatApi?.handleNewChat?.();
      return;
    }

    e.preventDefault();
    navigate("/chat");
  };

  return (
    <header
      className={[
        "left-0 top-0 w-full h-14",
        "px-4 sm:px-6 lg:px-8", //  모바일 16px 표준
        !isChatPage ? "fixed z-50" : "",
        !isHeroPage ? "bg-background" : "",
      ].join(" ")}
    >
      <div
        className={[
          "w-full h-14 flex items-center justify-between",
          !isHeroPage ? "border-b border-border" : "",
        ].join(" ")}
      >
        <a
          id="logo"
          href="/"
          onClick={handleLogoClick}
          className="text-lg md:text-xl text-foreground font-semibold" //  모바일에서만 한 단계 축소
        >
          Outfit Service
        </a>

        <div className="flex items-center gap-2">
          <DarkModeToggle />
          <MobileMenuButton
            onClick={() => {
              if (isChatPage) {
                // ✅ 모바일 햄버거 = 입력 패널 열기(아이템 입력)
                chatApi?.openInputPanel?.();
                setPanelCollapsed?.(false);
                return;
              }
              openMobileMenu();
            }}
          />
        </div>
      </div>
    </header>
  );
};

export default Header;
