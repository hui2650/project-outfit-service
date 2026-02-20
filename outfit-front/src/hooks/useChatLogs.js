import React from 'react'
import { useAppData } from '../store/appDataStore.jsx'

/**
 * useChatLogs()
 *
 * 목적
 * - 현재 선택된 세션(currentSessionId)의 chatLogs를 읽어오고
 * - 해당 세션에 turn을 추가하거나 업데이트하는 함수 제공
 *
 * 설계 의도
 * - 세션 기반 구조이기 때문에
 *   turn은 반드시 특정 sessionId에 귀속되어야 함
 * - sessionId를 명시적으로 받을 수도 있고,
 *   생략하면 현재 세션(currentSessionId)에 적용됨
 */
export const useChatLogs = () => {
  const { chatLogs, setChatSessions, currentSessionId } = useAppData()

  /**
   * appendTurn(turn, sessionIdParam?)
   *
   * 역할
   * - 특정 세션에 새로운 turn을 추가
   *
   * 동작 방식
   * 1. sessionIdParam이 있으면 그 세션에 추가
   * 2. 없으면 현재 선택된 세션(currentSessionId)에 추가
   * 3. setChatSessions로 전체 세션 배열을 map 돌며
   *    해당 세션만 turns 배열에 push
   *
   * 불변성 유지
   * - 기존 session 객체를 직접 수정하지 않고
   * - spread로 새 객체를 만들어 리턴
   */
  const appendTurn = React.useCallback(
    (turn, sessionIdParam) => {
      const sid = sessionIdParam ?? currentSessionId

      setChatSessions((prev) =>
        (prev ?? []).map((session) =>
          session.sessionId === sid
            ? { ...session, turns: [...(session.turns ?? []), turn] }
            : session
        )
      )
    },
    [setChatSessions, currentSessionId]
  )

  /**
   * updateTurn(turnId, updater, sessionIdParam?)
   *
   * 역할
   * - 특정 turn을 찾아 수정
   *
   * updater
   * - (oldTurn) => newTurn 형태의 함수
   * - 기존 turn을 받아 새로운 turn을 반환해야 함
   *
   * 동작 흐름
   * 1. sessionId 결정
   * 2. 해당 세션만 선택
   * 3. turns 배열을 map 돌며
   *    turn.id === turnId 인 항목만 updater 적용
   *
   * 사용 예
   * - loading → done 상태 변경
   * - 메시지 placeholder → 실제 답변으로 교체
   */
  const updateTurn = React.useCallback(
    (turnId, updater, sessionIdParam) => {
      const sid = sessionIdParam ?? currentSessionId

      setChatSessions((prev) =>
        (prev ?? []).map((session) => {
          if (session.sessionId !== sid) return session

          return {
            ...session,
            turns: (session.turns ?? []).map((t) =>
              t.id === turnId ? updater(t) : t
            ),
          }
        })
      )
    },
    [setChatSessions, currentSessionId]
  )

  return { chatLogs, appendTurn, updateTurn }
}
