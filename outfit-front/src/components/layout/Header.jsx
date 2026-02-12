import React from "react";
import { useLocation, Link } from "react-router-dom";
import DarkModeToggle from "../common/DarkModeToggle";

const Header = () => {
  const location = useLocation();
  const isHeroPage = location.pathname === "/";
  const chatPage = location.pathname === "/chat";

  return (
    <header
      className={`left-0 top-0 w-full h-14 px-8 ${!chatPage ? "fixed z-50 " : ""} `}
    >
      <div
        className={`w-full h-14 flex items-center justify-between ${!isHeroPage ? "border-b border-border" : ""}`}
      >
        <Link
          id="logo"
          to={location.pathname === "/" ? "/" : "/chat"}
          className="text-xl text-foreground"
        >
          Outfit Service
        </Link>
        <DarkModeToggle />
      </div>
    </header>
  );
};

export default Header;
