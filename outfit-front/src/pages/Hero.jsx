import React from 'react'

import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { useState } from 'react'

import Header from '../components/layout/Header'

const Hero = () => {
  const nav = useNavigate()
  const [leaving, setLeaving] = useState(false)

  const handleStart = () => {
    setLeaving(true)

    // 애니메이션 끝나고 이동
    setTimeout(() => {
      nav('/chat')
    }, 250)
  }

  return (
    <motion.div
      className="h-screen w-full bg-background"
      initial={{ opacity: 0 }}
      animate={{
        opacity: leaving ? 0 : 1,
        x: leaving ? -10 : 0,
      }}
      transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
    >
      {/* 배경/오버레이: 이미지가 있으면 여기에 background-image 적용 */}
      <Header />
      <div className="min-h-screen w-full bg-gradient-to-b from-black/60 via-black/40 to-black/70 flex items-center">
        <div className="w-full">
          <main className="mx-auto grid max-w-6xl grid-cols-1 gap-10 px-6 pb-14 pt-6 md:grid-cols-2 md:items-center">
            {/* Left */}
            <section className="text-white">
              <div className="text-xs tracking-widest text-primary/90">
                OUR SERVICE
              </div>

              <h1 className="mt-4 text-5xl font-extrabold leading-tight">
                AI 맞춤 코디 <br />
                <span className="text-white/95">STYLE AI</span>
              </h1>

              <p className="mt-6 max-w-md text-white/80 leading-relaxed">
                스타일AI는 AI기반 코디 추천 서비스입니다.
                <br />
                당신의 아이템을 입력하면, AI가 그에 맞는 코디와
                <br />
                스타일을 찾아드립니다.
              </p>

              <motion.button
                type="button"
                onClick={handleStart}
                whileHover={{ y: -5 }}
                whileTap={{ scale: 0.97 }}
                className="mt-10 w-full max-w-md rounded-2xl bg-white/10 hover:bg-white/15 border border-white/15 px-6 py-4 font-semibold flex items-center justify-center gap-3"
              >
                서비스 바로가기 <span aria-hidden>→</span>
              </motion.button>

              <div className="mt-10 flex flex-col items-center text-white/40 text-xs">
                <div className="h-7 w-5 rounded-full border border-white/20 flex items-start justify-center p-1">
                  <div className="h-2 w-1 rounded-full bg-white/30" />
                </div>
                <div className="mt-2 tracking-[0.3em]">SCROLL</div>
              </div>
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
      </div>
    </motion.div>
  )
}

export default Hero
