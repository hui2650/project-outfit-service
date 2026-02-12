import React from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { useTransition } from '../store/transitionStore'
import Header from '../components/layout/Header'

const UserPageStyle = () => {
  const nav = useNavigate()
  const { leaving, handleStart } = useTransition()

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{
        opacity: leaving ? 0 : 1,

        x: leaving ? -10 : 0,
      }}
      transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
      className="h-screen w-full flex flex-col items-center justify-center bg-background"
    >
      <Header />
      <div className=" flex flex-col items-center max-w-4xl ">
        <h1 className="text-4xl text-foreground mb-4 font-bold">
          어떤 스타일을 좋아하세요?
        </h1>
        <h3 className="text-lg text-secondary-foreground/80 mb-8">
          선호하시는 스타일에 맞춰서 추천해드릴게요
        </h3>
      </div>
      <div className="grid grid-cols-2 grid-rows-2 gap-6 w-full max-w-3xl px-4">
        {[
          { key: 'minimal', label: '미니멀' },
          { key: 'casual', label: '캐쥬얼' },
          { key: 'street', label: '스트릿' },
          { key: 'classic', label: '클래식' },
        ].map((style) => (
          <div
            key={style.key}
            className="
            h-40 
            rounded-2xl 
            border border-border 
            bg-card 
            flex items-center justify-center 
            text-xl font-semibold 
            text-foreground
            cursor-pointer
            transition-all duration-200
            hover:bg-muted
            hover:scale-[1.02]
      "
          >
            {style.label}
          </div>
        ))}
      </div>

      <div className="flex gap-4 mt-6">
        <button
          type="button"
          className="text-md px-5 py-2.5 rounded-lg bg-primary text-white font-semibold"
          onClick={() => handleStart(() => nav('/chat'))}
        >
          확인
        </button>
        <button
          type="button"
          className="text-md px-5 py-2.5 rounded-lg bg-gray-500 text-white font-semibold"
          onClick={() => handleStart(() => nav('/user-info-nickname'))}
        >
          뒤로
        </button>
      </div>
    </motion.div>
  )
}

export default UserPageStyle
