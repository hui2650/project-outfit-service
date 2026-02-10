import React from "react";

import { motion } from "framer-motion";

import HeroSectionWrapper from "./HeroSectionWrapper";

const HeroIntroSecond = ({ leaving, handleStart }) => {
  const bgStyle = {
    backgroundImage: `linear-gradient(to left,
        hsl(var(--background) / 0.6),
        hsl(var(--background) / 0.65),
        hsl(var(--background) / 0.8),
        hsl(var(--background) / 0.9)),
        url('/hero-bg-2.jpg')`,
  };

  return (
    <HeroSectionWrapper
      className="h-full w-full flex items-center

      bg-[linear-gradient(to_bottom,hsl(var(--background)/0.6),hsl(var(--background)/0.4),hsl(var(--background)/0.7)),url(/hero-bg.jpg)]

      bg-cover bg-center "
      initial={{ opacity: 0 }}
      animate={{
        opacity: leaving ? 0 : 1,

        x: leaving ? -10 : 0,
      }}
      style={bgStyle}
      transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
    >
      <div className="w-full">
        <main className="mx-auto grid max-w-6xl grid-cols-1 gap-10 px-6 pb-14 pt-6 md:grid-cols-2 md:items-center">
          {/* Left */}

          <section className="">
            <div className="text-xs tracking-widest text-primary/90">
              How It Works
            </div>

            <h1 className="mt-4 text-5xl font-extrabold text-foreground leading-tight">
              사진 한 장으로
              <br />
              <span className="text-foreground/95">OUTFIT MATCH</span>
            </h1>

            <p className="mt-6 max-w-md text-secondary-foreground/80 leading-relaxed">
              아이템 사진을 업로드하거나 텍스트로 설명해주세요.
              <br />
              AI가 8가지 코디 후보를 즉시 추천하고,
              <br />각 코디에 대한 스타일링 팁도 함께 알려드립니다.
            </p>

            <motion.button
              type="button"
              onClick={handleStart}
              whileHover={{ y: -5 }}
              whileTap={{ scale: 0.97 }}
              className="mt-10 w-full max-w-md rounded-2xl bg-card/10 hover:bg-card/15 
              border border-solid border-foreground/15
              px-6 py-4 font-semibold flex items-center justify-center gap-3"
            >
              지금 시작하기 <span aria-hidden>→</span>
            </motion.button>
          </section>

          {/* Right */}

          <section className="flex justify-center md:justify-end">
            <div className="w-[320px] h-[520px] rounded-[40px] border border-white/15 bg-white/5 shadow-2xl flex items-center justify-center">
              {/* 여기에 이미지/목업 넣기 */}

              <div className="w-[260px] h-[420px] rounded-[28px] bg-black/40 border border-white/10" />
            </div>
          </section>
        </main>
      </div>
    </HeroSectionWrapper>
  );
};

export default HeroIntroSecond;
