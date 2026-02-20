// src/components/hero/HeroSectionWrapper.jsx
import { motion } from 'framer-motion'

/*
HeroSectionWrapper
- 히어로 섹션 공통 래퍼
- 한 섹션을 h-screen으로 고정하여 스냅 스크롤과 잘 맞도록 설계
- style로 backgroundImage 등 동적 스타일을 받을 수 있도록 분리
*/
export default function HeroSectionWrapper({
  children,
  className,
  style,
  ...props
}) {
  return (
    <motion.section
      style={style}
      className={`h-screen w-full ${className}`}
      {...props}
    >
      {children}
    </motion.section>
  )
}
