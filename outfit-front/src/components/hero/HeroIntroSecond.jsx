import React from 'react'

import { motion } from 'framer-motion'

import HeroSectionWrapper from './HeroSectionWrapper'

const HeroIntroSecond = ({ leaving, handleStart }) => {
  const bgStyle = {
    backgroundImage: `linear-gradient(to left,
        hsl(var(--background) / 0.6),
        hsl(var(--background) / 0.65),
        hsl(var(--background) / 0.8),
        hsl(var(--background) / 0.9)),
        url('/hero-bg-2.jpg')`,
  }

  return (
    <HeroSectionWrapper
      className="h-full w-full bg-cover bg-center flex items-center"
      initial={{ opacity: 0 }}
      animate={{
        opacity: leaving ? 0 : 1,

        x: leaving ? -10 : 0,
      }}
      style={bgStyle}
      transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
    >
      <div className="w-full">
        <main className="mx-auto flex justify-between items-center max-w-6xl px-6 pb-14 pt-6">
          {/* Left */}

          <section className="mx-auto md:mx-0 flex flex-col md:justify-center">
            <div className="text-xs tracking-widest text-primary/90">
              How It Works
            </div>

            <h1 className="mt-4 text-5xl font-extrabold leading-tight text-foreground">
              사진 한 장으로
              <br />
              <span className="text-foreground/95">
                OUTFIT <br className="md:hidden" />
                MATCH
              </span>
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
              className="mt-10 w-[270px] lg:w-[450px] md:w-[320px] rounded-2xl bg-card/10 hover:bg-card/15 
              border border-solid border-foreground/15
              px-6 py-4 font-semibold flex items-center justify-center gap-3"
            >
              지금 시작하기 <span aria-hidden>→</span>
            </motion.button>
          </section>

          {/* Right */}

          <section className="flex justify-center-end hidden md:block">
            <div className="w-[300px] h-[640px] rounded-[40px] border border-white/15 bg-white/5 shadow-2xl flex items-center justify-center overflow-hidden">
              {/* 여기에 이미지/목업 넣기 */}
              <img
                src="/mobile-img-2.PNG"
                alt=""
                className="h-full object-cover"
              />
            </div>
          </section>
        </main>
      </div>
    </HeroSectionWrapper>
  )
}

export default HeroIntroSecond
