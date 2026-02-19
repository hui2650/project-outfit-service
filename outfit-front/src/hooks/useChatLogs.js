import React from 'react'
import { useAppData } from '../store/appDataStore.jsx'

export const useChatLogs = () => {
  const { chatLogs, setChatSessions, currentSessionId } = useAppData()

  // sessionId를 선택적으로 받도록 변경
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
