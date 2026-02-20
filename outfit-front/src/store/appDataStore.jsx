// src/store/appDataStore.jsx
// 단일 전역 스토어
// - favorites / history / chatSessions / guest / currentSessionId 를 한 Provider에서 관리
// - localStorage 영속화 + 세션/턴 업데이트 유틸 포함
// - 별도 FavoritesProvider(favoriteStore)는 제거하고, 모든 컴포넌트는 useAppData()만 사용

import React from 'react'

const Ctx = React.createContext(null)

/*
load(key, fallback)
- localStorage에서 JSON 값을 읽어 파싱
- 파싱 실패/권한 문제/스토리지 비활성화 등 예외가 나도 fallback으로 계속 동작
*/
const load = (key, fallback) => {
  try {
    const raw = localStorage.getItem(key)
    return raw ? JSON.parse(raw) : fallback
  } catch {
    return fallback
  }
}

/*
safeSet(key, value)
- localStorage 저장 유틸
- 실패해도 앱이 중단되지 않도록 방어
*/
const safeSet = (key, value) => {
  try {
    localStorage.setItem(key, JSON.stringify(value))
  } catch {}
}

/*
initialGuest
- 게스트 사용자 입력 정보 초기값
- guestId: 게스트 사용자를 식별하는 id
- nickname/style: 유저정보 입력 플로우에서 채워짐
*/
const initialGuest = {
  guestId: null,
  nickname: '',
  style: '',
}

/*
genId(prefix?)
- 고유 id 생성 (세션/게스트 등에 사용)
- crypto.randomUUID가 있으면 UUID 사용
- 없으면 Date.now 기반 문자열로 폴백
*/
const genId = (prefix = '') => {
  const base =
    typeof crypto !== 'undefined' && crypto.randomUUID
      ? crypto.randomUUID()
      : String(Date.now())
  return prefix ? `${prefix}${base}` : base
}

/*
getNextSessionTitle(sessions)
- "새 채팅", "새 채팅 N" 규칙으로 다음 세션 제목 생성
- 기존 세션들에서 가장 큰 N을 찾아 +1
*/
const getNextSessionTitle = (sessions) => {
  let max = 0

  for (const s of sessions ?? []) {
    const t = (s?.title ?? '').trim()

    if (t === '새 채팅') {
      max = Math.max(max, 1)
      continue
    }

    const m = /^새\s*채팅\s*(\d+)$/.exec(t)
    if (m) max = Math.max(max, Number(m[1]))
  }

  return `새 채팅 ${max + 1}`
}

/*
normalizeTitle(title)
- 세션 제목 저장 시 공백/빈 문자열 방지
*/
const normalizeTitle = (title) => {
  const t = String(title ?? '').trim()
  return t.length ? t : '새 채팅'
}

export const AppDataProvider = ({ children }) => {
  /*
  상태 초기화
  - lazy initializer를 사용해 최초 1회만 localStorage를 읽음
  */
  const [favorites, setFavorites] = React.useState(() => load('favorites', []))
  const [history, setHistory] = React.useState(() => load('history', []))
  const [chatSessions, setChatSessions] = React.useState(() =>
    load('chatSessions', [])
  )
  const [currentSessionId, setCurrentSessionId] = React.useState(() =>
    load('currentSessionId', null)
  )
  const [guest, setGuestState] = React.useState(() =>
    load('guest', initialGuest)
  )

  /*
  localStorage 동기화
  - 각 state 변경 시 해당 key를 갱신
  - 저장 실패는 무시(앱 런타임 안정성 우선)
  */
  React.useEffect(() => {
    safeSet('favorites', favorites)
  }, [favorites])

  React.useEffect(() => {
    safeSet('history', history)
  }, [history])

  React.useEffect(() => {
    safeSet('chatSessions', chatSessions)
  }, [chatSessions])

  React.useEffect(() => {
    safeSet('currentSessionId', currentSessionId)
  }, [currentSessionId])

  React.useEffect(() => {
    safeSet('guest', guest)
  }, [guest])

  /*
  currentSessionId 보정
  - sessions가 0개면 currentSessionId를 null로 유지
  - currentSessionId가 없거나(초기/손상) 존재하지 않으면 첫 세션으로 보정
  */
  React.useEffect(() => {
    const sessions = chatSessions ?? []

    if (sessions.length === 0) {
      if (currentSessionId !== null) setCurrentSessionId(null)
      return
    }

    const exists = sessions.some((s) => s?.sessionId === currentSessionId)
    if (!currentSessionId || !exists) {
      setCurrentSessionId(sessions[0]?.sessionId ?? null)
    }
  }, [chatSessions, currentSessionId])

  /*
  파생 값: 현재 세션 객체
  - currentSessionId가 가리키는 세션을 찾아 반환
  - 없으면 null
  */
  const currentSession = React.useMemo(() => {
    return (
      (chatSessions ?? []).find((s) => s.sessionId === currentSessionId) ?? null
    )
  }, [chatSessions, currentSessionId])

  /*
  파생 값: 현재 세션의 turns
  - UI(ResultStage)가 바로 사용할 수 있는 형태
  */
  const chatLogs = currentSession?.turns ?? []

  /*
  isLiked(item)
  - favorites 목록에 itemKey가 존재하면 true
  - itemKey를 동일성 기준으로 사용
  */
  const isLiked = React.useCallback(
    (item) => (favorites ?? []).some((x) => x.itemKey === item.itemKey),
    [favorites]
  )

  /*
  toggleLike(item)
  - favorites 토글
  - 존재하면 제거, 없으면 likedAt을 붙여 맨 앞에 추가(최신 좋아요 우선)
  */
  const toggleLike = React.useCallback((item) => {
    setFavorites((prev) => {
      const base = prev ?? []
      const exists = base.some((x) => x.itemKey === item.itemKey)
      return exists
        ? base.filter((x) => x.itemKey !== item.itemKey)
        : [{ ...item, likedAt: Date.now() }, ...base]
    })
  }, [])

  /*
  addHistoryTurn(historyTurn)
  - 요청 단위 히스토리 저장
  - 최신 항목을 앞에 넣고 최대 50개로 제한
  */
  const addHistoryTurn = React.useCallback((historyTurn) => {
    setHistory((prev) => [historyTurn, ...(prev ?? [])].slice(0, 50))
  }, [])

  /*
  guest 관련 유틸
  */

  /*
  setGuest(payload)
  - guest 정보를 부분 업데이트(merge)
  */
  const setGuest = React.useCallback((payload) => {
    setGuestState((prev) => ({
      ...(prev ?? initialGuest),
      ...(payload ?? {}),
    }))
  }, [])

  /*
  ensureGuestId()
  - guestId가 없을 때만 생성
  - 게스트 플로우에서 guestId를 안정적으로 보장하기 위해 사용
  */
  const ensureGuestId = React.useCallback(() => {
    setGuestState((prev) => {
      const base = prev ?? initialGuest
      if (base.guestId) return base
      return { ...base, guestId: genId('g_') }
    })
  }, [])

  /*
  resetGuest()
  - guest를 초기화
  - state 갱신 + localStorage 즉시 갱신(새로고침에도 초기화 유지)
  */
  const resetGuest = React.useCallback(() => {
    setGuestState(initialGuest)
    safeSet('guest', initialGuest)
  }, [])

  /*
  세션 관련 유틸
  */

  /*
  createNewSession()
  - 새 채팅 세션 생성(최신을 앞에)
  - 생성 즉시 currentSessionId를 새 세션으로 전환
  - 반환 sessionId는 "요청 시작 시점 세션 고정"에 유용
  */
  const createNewSession = React.useCallback(() => {
    const sessionId = genId()
    const createdAt = Date.now()

    setChatSessions((prev) => {
      const base = prev ?? []
      const title = getNextSessionTitle(base)
      const newSession = { sessionId, createdAt, title, turns: [] }
      return [newSession, ...base]
    })

    setCurrentSessionId(sessionId)
    return sessionId
  }, [])

  /*
  selectSession(sessionId)
  - 현재 선택 세션 변경
  - null 허용(세션 0개 상태 표현)
  */
  const selectSession = React.useCallback((sessionId) => {
    setCurrentSessionId(sessionId ?? null)
  }, [])

  /*
  renameSession(sessionId, title)
  - 세션 제목 변경
  - normalizeTitle로 빈 제목 방지
  */
  const renameSession = React.useCallback((sessionId, title) => {
    const nextTitle = normalizeTitle(title)

    setChatSessions((prev) =>
      (prev ?? []).map((s) =>
        s.sessionId === sessionId ? { ...s, title: nextTitle } : s
      )
    )
  }, [])

  /*
  deleteSession(sessionId)
  - 세션 제거
  - 삭제 대상이 현재 세션이면 남은 첫 세션으로 이동, 없으면 null
  */
  const deleteSession = React.useCallback((sessionId) => {
    setChatSessions((prev) => {
      const remaining = (prev ?? []).filter((s) => s.sessionId !== sessionId)

      setCurrentSessionId((cur) => {
        if (cur !== sessionId) return cur
        return remaining[0]?.sessionId ?? null
      })

      return remaining
    })
  }, [])

  /*
  turn 관련 유틸 (비동기 안전성의 핵심)

  appendTurnToSession(sessionId, turn)
  - currentSessionId에 의존하지 않고 sessionId로 직접 지정
  - 요청 도중 사용자가 세션을 바꿔도, "요청이 시작된 세션"에 turn이 정확히 붙도록 보장
  */
  const appendTurnToSession = React.useCallback((sessionId, turn) => {
    if (!sessionId || !turn) return

    setChatSessions((prev) =>
      (prev ?? []).map((s) =>
        s.sessionId === sessionId
          ? { ...s, turns: [...(s.turns ?? []), turn] }
          : s
      )
    )
  }, [])

  /*
  updateTurnById(turnId, updater)
  - 모든 세션을 순회하며 turnId를 찾아 업데이트
  - currentSessionId에 의존하지 않으므로, 화면에서 보고 있는 세션과 무관하게 정확히 갱신 가능
  - updater는 (prevTurn) => nextTurn 형태의 순수 함수로 기대
  */
  const updateTurnById = React.useCallback((turnId, updater) => {
    if (!turnId || typeof updater !== 'function') return

    setChatSessions((prev) =>
      (prev ?? []).map((s) => {
        const turns = s.turns ?? []
        const idx = turns.findIndex((t) => t?.id === turnId)
        if (idx < 0) return s

        const nextTurns = [...turns]
        nextTurns[idx] = updater(nextTurns[idx])
        return { ...s, turns: nextTurns }
      })
    )
  }, [])

  /*
  context로 노출할 API
  - useMemo로 참조 안정성을 확보하여 불필요한 리렌더를 감소
  */
  const value = React.useMemo(
    () => ({
      // read
      chatSessions,
      currentSessionId,
      chatLogs,

      // session actions
      createNewSession,
      selectSession,
      renameSession,
      deleteSession,

      // turn actions
      appendTurnToSession,
      updateTurnById,

      // guest
      guest,
      setGuest,
      ensureGuestId,
      resetGuest,

      // favorites/history
      favorites,
      toggleLike,
      isLiked,
      history,
      addHistoryTurn,
    }),
    [
      // favorites/history
      favorites,
      toggleLike,
      isLiked,
      history,
      addHistoryTurn,

      // sessions
      chatSessions,
      currentSessionId,
      chatLogs,
      createNewSession,
      selectSession,
      renameSession,
      deleteSession,

      // turns
      appendTurnToSession,
      updateTurnById,

      // guest
      guest,
      setGuest,
      ensureGuestId,
      resetGuest,
    ]
  )

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export const useAppData = () => {
  const v = React.useContext(Ctx)
  if (!v) throw new Error('useAppData must be used within AppDataProvider')
  return v
}
