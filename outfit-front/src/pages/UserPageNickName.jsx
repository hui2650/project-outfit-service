import React from 'react'
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import Header from '../components/layout/Header'
import { useTransition } from '../store/transitionStore'

const UserPageNickName = () => {
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

      <div className="flex flex-col items-center max-w-4xl">
        <h1 className="text-4xl text-foreground mb-4 font-bold">
          닉네임을 입력해주세요
        </h1>
        <h3 className="text-lg text-secondary-foreground/80 mb-8">
          당신의 스타일을 찾기 위해 닉네임을 알려주세요.
        </h3>

        <input
          type="text"
          className="w-full h-10 rounded-xl p-3 bg-transparent outline-none text-md
          border border-border
          focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring
          focus-visible:ring-offset-2 focus-visible:ring-offset-background
          placeholder:text-muted-foreground disabled:opacity-60"
        />
      </div>

      <div className="flex gap-4 mt-6">
        <button
          type="button"
          className="text-md px-5 py-2.5 rounded-lg bg-primary text-white font-semibold disabled:opacity-60"
          disabled={leaving}
          onClick={() => handleStart(() => nav('/user-info-style'))}
        >
          확인
        </button>

        <button
          type="button"
          className="text-md px-5 py-2.5 rounded-lg bg-gray-500 text-white font-semibold disabled:opacity-60"
          disabled={leaving}
          onClick={() => handleStart(() => nav('/'))}
        >
          뒤로
        </button>
      </div>
    </motion.div>
  )
}

export default UserPageNickName
