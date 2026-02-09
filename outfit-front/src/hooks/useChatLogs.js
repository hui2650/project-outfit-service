import { useState } from 'react'

/**
 * useChatLogs()
 *
 * 역할
 * - 채팅 기록(chatLogs)을 "turn 배열"로 관리하는 전용 훅
 * - Home.jsx가 너무 길어지는 것을 줄이기 위해 상태/함수를 분리한 것
 *
 * chatLogs 구조(중요)
 * - chatLogs = [turn, turn, turn, ...]
 * - 각 turn 안에 messages 배열이 있고, UI는 messages만 보고 렌더함
 *
 * 이 훅이 제공하는 API
 * 1) chatLogs: 현재 전체 turn 목록
 * 2) setChatLogs: 필요할 때 전체를 직접 갈아끼우는 용도(되도록 최소화)
 * 3) appendTurn(turn): 새 turn을 맨 뒤에 추가
 * 4) updateTurn(turnId, updater): 특정 turn만 찾아서 안전하게 업데이트
 *
 * updateTurn이 핵심인 이유
 * - React state는 "불변 업데이트"가 기본 철학
 * - turn 하나만 수정할 때 전체를 직접 조작하면 버그가 잘 생김
 * - updateTurn은 "해당 turn만 골라 updater(t)"로 새 객체를 만들어주니 안정적
 */

export const useChatLogs = () => {
  /**
   * chatLogs 상태
   * - turn 배열
   * - 초기값은 빈 배열(아직 추천 기록 없음)
   */
  const [chatLogs, setChatLogs] = useState([])

  /**
   * appendTurn(turn)
   * - 새로운 turn(=요청 1회)을 chatLogs 마지막에 추가
   *
   * 왜 setChatLogs(prev => ...) 형태를 쓰나?
   * - React state 업데이트는 비동기/배치될 수 있음
   * - 이전 값을 안전하게 기반으로 업데이트하려면 함수형 업데이트를 써야 함
   */
  const appendTurn = (turn) => {
    setChatLogs((prev) => [...prev, turn])
  }

  /**
   * updateTurn(turnId, updater)
   * - chatLogs에서 특정 turnId를 가진 turn만 찾아서 업데이트
   *
   * 사용 예시
   * - 서버 응답이 오면:
   *   updateTurn(turnId, (t) => ({ ...t, status:'done', messages:[...t.messages, ...] }))
   *
   * updater(t) 설계 의도
   * - 업데이트 규칙을 호출하는 쪽(Home/useRecommend)에서 유연하게 정의 가능
   * - 이 훅은 "찾아서 갈아끼우는 작업"만 책임진다 (역할 분리)
   */
  const updateTurn = (turnId, updater) => {
    setChatLogs((prev) => prev.map((t) => (t.id === turnId ? updater(t) : t)))
  }

  return {
    chatLogs, // 화면에 렌더할 turn 목록
    setChatLogs, // 전체 교체 필요 시(가능하면 최소 사용)
    appendTurn, // 새 turn 추가
    updateTurn, // 특정 turn 업데이트(응답/에러 처리에 핵심)
  }
}
