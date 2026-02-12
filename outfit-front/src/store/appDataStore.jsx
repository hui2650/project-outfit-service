import React from "react";

const Ctx = React.createContext(null);

export const AppDataProvider = ({ children }) => {
  // ❌ KHÔNG load từ localStorage nữa
  const [favorites, setFavorites] = React.useState([]);
  const [history, setHistory] = React.useState([]);
  const [chatSessions, setChatSessions] = React.useState([]);
  const [currentSessionId, setCurrentSessionId] = React.useState(null);

  const [guest, setGuestState] = React.useState({
    guestId: null,
    nickname: "",
    style: "",
  });

  // 첫 실행: 세션 하나 자동 생성
  React.useEffect(() => {
    if (chatSessions.length === 0) {
      const first = {
        sessionId: crypto.randomUUID(),
        createdAt: Date.now(),
        title: "새 채팅",
        turns: [],
      };
      setChatSessions([first]);
      setCurrentSessionId(first.sessionId);
      return;
    }

    if (!currentSessionId) {
      setCurrentSessionId(chatSessions[0].sessionId);
    }
  }, [chatSessions, currentSessionId]);

  const isLiked = React.useCallback(
    (item) => favorites.some((x) => x.itemKey === item.itemKey),
    [favorites],
  );

  const currentSession = React.useMemo(() => {
    return chatSessions.find((s) => s.sessionId === currentSessionId) ?? null;
  }, [chatSessions, currentSessionId]);

  const chatLogs = currentSession?.turns ?? [];

  const setGuest = React.useCallback((payload) => {
    setGuestState((prev) => ({ ...prev, ...payload }));
  }, []);

  const ensureGuestId = React.useCallback(() => {
    setGuestState((prev) => {
      if (prev?.guestId) return prev;
      const id =
        typeof crypto !== "undefined" && crypto.randomUUID
          ? `g_${crypto.randomUUID()}`
          : `g_${Date.now()}`;
      return { ...(prev ?? {}), guestId: id };
    });
  }, []);

  const createNewSession = React.useCallback(() => {
    const newSession = {
      sessionId: crypto.randomUUID(),
      createdAt: Date.now(),
      title: "새 채팅",
      turns: [],
    };

    setChatSessions((prev) => [newSession, ...prev]);
    setCurrentSessionId(newSession.sessionId);
  }, []);

  const toggleLike = React.useCallback((item) => {
    setFavorites((prev) => {
      const exists = prev.some((x) => x.itemKey === item.itemKey);
      return exists
        ? prev.filter((x) => x.itemKey !== item.itemKey)
        : [{ ...item, likedAt: Date.now() }, ...prev];
    });
  }, []);

  const addHistoryTurn = React.useCallback((historyTurn) => {
    setHistory((prev) => [historyTurn, ...prev].slice(0, 50));
  }, []);

  const value = React.useMemo(
    () => ({
      favorites,
      toggleLike,
      isLiked,
      history,
      addHistoryTurn,
      setFavorites,
      setHistory,

      // chat
      chatSessions,
      setChatSessions,
      currentSessionId,
      setCurrentSessionId,
      createNewSession,

      // derived
      chatLogs,

      // guest
      guest,
      setGuest,
      ensureGuestId,
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
      guest,
      setGuest,
      ensureGuestId,
    ],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
};

export const useAppData = () => {
  const v = React.useContext(Ctx);
  if (!v) throw new Error("useAppData must be used within AppDataProvider");
  return v;
};
