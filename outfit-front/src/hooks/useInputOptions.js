import { useState } from 'react'

/**
 * useInputOptions()
 *
 * 목적
 * - 아이템 추천 요청에 필요한 입력 상태를 묶어서 관리
 * - 텍스트/카테고리/성별을 하나의 훅으로 추상화
 *
 * 설계 이유
 * - Home 컴포넌트에 useState가 난립하는 것을 방지
 * - 입력 관련 state를 한 덩어리로 관리
 */
export function useInputOptions() {
  const [textQuery, setTextQuery] = useState('')
  const [category, setCategory] = useState(null)
  const [gender, setGender] = useState(null)

  /**
   * reset()
   *
   * 역할
   * - 입력값을 초기 상태로 되돌림
   * - 추천 성공 후 폼 정리용
   */
  const reset = () => {
    setTextQuery('')
    setCategory(null)
    setGender(null)
  }

  return {
    textQuery,
    setTextQuery,
    category,
    setCategory,
    gender,
    setGender,
    reset,
  }
}
