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

  const isLiked = React.useCallback(
    (item) => favorites.some((x) => x.itemKey === item.itemKey),
    [favorites]
  )

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
    }),
    [favorites, history, isLiked, toggleLike, addHistoryTurn]
  )

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export const useAppData = () => {
  const v = React.useContext(Ctx)
  if (!v) throw new Error('useAppData must be used within AppDataProvider')
  return v
}
