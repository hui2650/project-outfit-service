import React, { useRef } from "react";
import { useTransition } from "../store/transitionStore";
import { useNavigate } from "react-router-dom";

import Header from "../components/layout/Header";

import usePagingSnap from "../hooks/usePagingSnap";
import HeroIntroFirst from "../components/hero/HeroIntroFirst";
import HeroIntroSecond from "../components/hero/HeroIntroSecond";

const Hero = () => {
  const nav = useNavigate();
  const { leaving, handleStart } = useTransition();

  const scrollerRef = useRef(null);

  usePagingSnap(scrollerRef, {
    selector: "[data-hero-section]",
    lockMs: 900,
    wheelThreshold: 40,
    swipeThresholdPx: 60,
    durationMs: 650,
  });

  return (
    <div className="h-screen overflow-hidden">
      <Header />

      <div ref={scrollerRef} className="h-full overflow-y-auto scroll-smooth">
        <div data-hero-section>
          <HeroIntroFirst
            leaving={leaving}
            handleStart={() => handleStart(() => nav("/nicknameinput"))}
          />
        </div>

        <div data-hero-section>
          <HeroIntroSecond
            leaving={leaving}
            handleStart={() => handleStart(() => nav("/nicknameinput"))}
          />
        </div>
      </div>
    </div>
  );
};

export default Hero;
