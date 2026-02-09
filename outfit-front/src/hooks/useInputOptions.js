// src/hooks/useInputOptions.js
import { useState } from 'react'

/**
 * useInputOptions()
 * - "텍스트/카테고리/성별" 입력 옵션을 한 덩어리로 관리하는 훅
 *
 * 목적
 * - Home.jsx에서 useState 3개를 계속 들고 있으면 파일이 길어짐
 * - 입력 관련 state를 묶어서 관리하면 props 전달도 깔끔해짐
 *
 * 포함하는 state
 * - textQuery: 검색 보조 텍스트(옵션)
 * - category: 필수 선택값 (예: top/bottom/shoes...)
 * - gender: 필수 선택값 (예: man/woman)
 *
 * reset()
 * - "제출 성공" 같은 순간에 입력값을 초기화하는 용도
 * - 실패 시 reset을 하면 사용자가 다시 입력해야 해서 UX가 나빠질 수 있음
 *   => 보통 성공했을 때만 reset 권장
 */
export function useInputOptions() {
  const [textQuery, setTextQuery] = useState('')
  const [category, setCategory] = useState(null)
  const [gender, setGender] = useState(null)

  /**
   * reset()
   * - 옵션 입력값을 초기값으로 되돌림
   * - 제출 성공 후, 다음 요청을 위해 입력 폼을 비워줄 때 사용
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
