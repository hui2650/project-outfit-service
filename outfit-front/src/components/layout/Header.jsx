import React from "react";
import { useLocation, useNavigate } from "react-router-dom";
import DarkModeToggle from "../common/DarkModeToggle";
import { useChatPage } from "../../pages/chat/ChatPageContext"; // 경로 맞게 수정

const USER_INFO_PATHS = new Set([
  "/",
  "/user-info-style",
  "/user-info-nickname",
]);

const Header = () => {
  const location = useLocation();
  const navigate = useNavigate();

  const pathname = location.pathname;
  const isHeroPage = pathname === "/";
  const isChatPage = pathname === "/chat";
  const isUserInfoPage = USER_INFO_PATHS.has(pathname);

  // ChatPageProvider 밖에서 Header가 렌더될 수 있으니 안전하게 try
  let chatApi = null;
  try {
    chatApi = useChatPage();
  } catch {}

  const handleLogoClick = (e) => {
    // 1) 유저정보 입력 페이지는 "리로드"가 요구사항
    if (isUserInfoPage) {
      e.preventDefault();
      // react-router 방식 리로드
      navigate(0); // = window.location.reload() 같은 효과
      return;
    }

    // 2) /chat에서는 새 대화 시작(리셋)
    if (isChatPage) {
      e.preventDefault();
      chatApi?.handleNewChat?.();
      return;
    }

    // 3) 그 외 페이지는 /chat로 이동(기존 채팅 유지)
    e.preventDefault();
    navigate("/chat");
  };

  return (
    <header
      className={`left-0 top-0 w-full h-14 px-8 ${
        !isChatPage ? "fixed z-50" : ""
      } ${!isHeroPage ? "bg-background" : ""}`}
    >
      <div
        className={`w-full h-14 flex items-center justify-between ${
          !isHeroPage ? "border-b border-border" : ""
        }`}
      >
        <a
          id="logo"
          href={isHeroPage ? "/" : "/"}
          onClick={handleLogoClick}
          className="text-xl text-foreground"
        >
          Outfit Service
        </a>

        <DarkModeToggle />
      </div>
    </header>
  );
};

export default Header;
