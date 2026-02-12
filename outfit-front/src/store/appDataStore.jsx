import React from 'react'

const Ctx = React.createContext(null)

const load = (key, fallback) => {
  try {
    const raw = localStorage.getItem(key)
    return raw ? JSON.parse(raw) : fallback
  } catch {
    return fallback
  }
}

export const AppDataProvider = ({ children }) => {
  const [favorites, setFavorites] = React.useState(() => load('favorites', []))
  const [history, setHistory] = React.useState(() => load('history', []))
  const [chatSessions, setChatSessions] = React.useState(() =>
    load('chatSessions', [])
  )
  const [currentSessionId, setCurrentSessionId] = React.useState(() =>
    load('currentSessionId', null)
  )

  React.useEffect(() => {
    try {
      localStorage.setItem('favorites', JSON.stringify(favorites))
    } catch {}
  }, [favorites])

  React.useEffect(() => {
    try {
      localStorage.setItem('history', JSON.stringify(history))
    } catch {}
  }, [history])

  React.useEffect(() => {
    try {
      localStorage.setItem('chatSessions', JSON.stringify(chatSessions))
    } catch {}
  }, [chatSessions])

  React.useEffect(() => {
    try {
      localStorage.setItem('currentSessionId', JSON.stringify(currentSessionId))
    } catch {}
  }, [currentSessionId])

  React.useEffect(() => {
    if (chatSessions.length === 0) {
      // 첫 실행: 세션 하나 만들어주기
      const first = {
        sessionId: crypto.randomUUID(),
        createdAt: Date.now(),
        title: '새 채팅',
        turns: [],
      }
      setChatSessions([first])
      setCurrentSessionId(first.sessionId)
      return
    }

    // currentSessionId가 없으면 첫 세션으로
    if (!currentSessionId) {
      setCurrentSessionId(chatSessions[0].sessionId)
    }
  }, [chatSessions, currentSessionId])

  const isLiked = React.useCallback(
    (item) => favorites.some((x) => x.itemKey === item.itemKey),
    [favorites]
  )

  const currentSession = React.useMemo(() => {
    return chatSessions.find((s) => s.sessionId === currentSessionId) ?? null
  }, [chatSessions, currentSessionId])

  const chatLogs = currentSession?.turns ?? []

  const createNewSession = React.useCallback(() => {
    const newSession = {
      sessionId: crypto.randomUUID(),
      createdAt: Date.now(),
      title: '새 채팅',
      turns: [],
    }

    setChatSessions((prev) => [newSession, ...prev])
    setCurrentSessionId(newSession.sessionId)
  }, [])

  const toggleLike = React.useCallback((item) => {
    setFavorites((prev) => {
      const exists = prev.some((x) => x.itemKey === item.itemKey)
      return exists
        ? prev.filter((x) => x.itemKey !== item.itemKey)
        : [{ ...item, likedAt: Date.now() }, ...prev]
    })
  }, [])

  const addHistoryTurn = React.useCallback((historyTurn) => {
    setHistory((prev) => [historyTurn, ...prev].slice(0, 50))
  }, [])

  const value = React.useMemo(
    () => ({
      favorites,
      toggleLike,
      isLiked,
      history,
      addHistoryTurn,
      setFavorites,
      setHistory,

      //  chat
      chatSessions,
      setChatSessions,
      currentSessionId,
      setCurrentSessionId,
      createNewSession,

      //  derived
      chatLogs,
    }),
    [
      favorites,
      history,
      isLiked,
      toggleLike,
      addHistoryTurn,
      chatSessions,
      currentSessionId,

      chatLogs,
    ]
  )

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export const useAppData = () => {
  const v = React.useContext(Ctx)
  if (!v) throw new Error('useAppData must be used within AppDataProvider')
  return v
}
