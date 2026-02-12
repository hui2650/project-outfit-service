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

const initialGuest = {
  guestId: null,
  nickname: "",
  style: "",
};

const getNextSessionTitle = (sessions) => {
  // "새 채팅", "새 채팅 1", "새 채팅 2" 등에서 최대 번호를 찾아 +1
  // "새 채팅"만 있는 건 1로 취급
  let max = 0;

  for (const s of sessions ?? []) {
    const t = (s?.title ?? "").trim();
    if (t === "새 채팅") {
      max = Math.max(max, 1);
      continue;
    }
    const m = /^새\s*채팅\s*(\d+)$/.exec(t);
    if (m) max = Math.max(max, Number(m[1]));
  }

  const next = max + 1;
  return `새 채팅 ${next}`;
};

const normalizeTitle = (title) => {
  const t = String(title ?? "").trim();
  return t.length ? t : "새 채팅";
};

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
    if ((chatSessions ?? []).length === 0) {
      // 첫 실행: 세션 하나 만들어주기
      const first = {
        sessionId:
          typeof crypto !== "undefined" && crypto.randomUUID
            ? crypto.randomUUID()
            : String(Date.now()),
        createdAt: Date.now(),
<<<<<<< Updated upstream
        title: '새 채팅',
=======
        title: getNextSessionTitle([]), // 새 채팅 1
>>>>>>> Stashed changes
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
<<<<<<< Updated upstream
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
=======
    return (
      (chatSessions ?? []).find((s) => s.sessionId === currentSessionId) ?? null
    );
  }, [chatSessions, currentSessionId]);

  const chatLogs = currentSession?.turns ?? [];

  const setGuest = React.useCallback((payload) => {
    setGuestState((prev) => ({
      ...(prev ?? initialGuest),
      ...(payload ?? {}),
    }));
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

  const resetGuest = React.useCallback(() => {
    setGuestState(initialGuest);
    try {
      localStorage.setItem("guest", JSON.stringify(initialGuest));
    } catch {}
  }, []);

  // 세션 생성 함수
  const createNewSession = React.useCallback(() => {
    const sessionId =
      typeof crypto !== "undefined" && crypto.randomUUID
        ? crypto.randomUUID()
        : String(Date.now());

    const createdAt = Date.now();

    setChatSessions((prev) => {
      const base = prev ?? [];
      const title = getNextSessionTitle(base);
      const newSession = { sessionId, createdAt, title, turns: [] };
      return [newSession, ...base];
    });

    setCurrentSessionId(sessionId);
  }, []);

  // 세션 제목 변경 함수
  const renameSession = React.useCallback((sessionId, title) => {
    const nextTitle = normalizeTitle(title);

    setChatSessions((prev) =>
      (prev ?? []).map((s) =>
        s.sessionId === sessionId ? { ...s, title: nextTitle } : s,
      ),
    );
  }, []);

  // 세션 삭제 함수
  const deleteSession = React.useCallback((sessionId) => {
    setChatSessions((prev) => {
      const remaining = (prev ?? []).filter((s) => s.sessionId !== sessionId);

      setCurrentSessionId((cur) => {
        if (cur !== sessionId) return cur;
        return remaining[0]?.sessionId ?? null;
      });

      return remaining;
    });
  }, []);

  const toggleLike = React.useCallback((item) => {
    setFavorites((prev) => {
      const exists = (prev ?? []).some((x) => x.itemKey === item.itemKey);
      return exists
        ? (prev ?? []).filter((x) => x.itemKey !== item.itemKey)
        : [{ ...item, likedAt: Date.now() }, ...(prev ?? [])];
    });
  }, []);

  const addHistoryTurn = React.useCallback((historyTurn) => {
    setHistory((prev) => [historyTurn, ...(prev ?? [])].slice(0, 50));
  }, []);
>>>>>>> Stashed changes

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
      renameSession,
      deleteSession,

      // derived
      chatLogs,
<<<<<<< Updated upstream
=======

      // guest
      guest,
      setGuest,
      ensureGuestId,
      resetGuest,
>>>>>>> Stashed changes
    }),
    [
      favorites,
      history,
      isLiked,
      toggleLike,
      addHistoryTurn,
      chatSessions,
      currentSessionId,
      renameSession,
      deleteSession,
      chatLogs,
<<<<<<< Updated upstream
    ]
  )

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}
=======
      guest,
      setGuest,
      ensureGuestId,
      resetGuest,
    ],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
};
>>>>>>> Stashed changes

export const useAppData = () => {
  const v = React.useContext(Ctx)
  if (!v) throw new Error('useAppData must be used within AppDataProvider')
  return v
}
