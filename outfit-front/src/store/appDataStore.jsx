import React from "react";

const Ctx = React.createContext(null);

const load = (key, fallback) => {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
};

const initialGuest = {
  guestId: null,
  nickname: "",
  style: "",
};

const genId = (prefix = "") => {
  const base =
    typeof crypto !== "undefined" && crypto.randomUUID
      ? crypto.randomUUID()
      : String(Date.now());
  return prefix ? `${prefix}${base}` : base;
};

const getNextSessionTitle = (sessions) => {
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

  return `새 채팅 ${max + 1}`;
};

const normalizeTitle = (title) => {
  const t = String(title ?? "").trim();
  return t.length ? t : "새 채팅";
};

export const AppDataProvider = ({ children }) => {
  const [favorites, setFavorites] = React.useState(() => load("favorites", []));
  const [history, setHistory] = React.useState(() => load("history", []));
  const [chatSessions, setChatSessions] = React.useState(() =>
    load("chatSessions", []),
  );
  const [currentSessionId, setCurrentSessionId] = React.useState(() =>
    load("currentSessionId", null),
  );
  const [guest, setGuestState] = React.useState(() =>
    load("guest", initialGuest),
  );

  React.useEffect(() => {
    try {
      localStorage.setItem("favorites", JSON.stringify(favorites));
    } catch {}
  }, [favorites]);

  React.useEffect(() => {
    try {
      localStorage.setItem("history", JSON.stringify(history));
    } catch {}
  }, [history]);

  React.useEffect(() => {
    try {
      localStorage.setItem("chatSessions", JSON.stringify(chatSessions));
    } catch {}
  }, [chatSessions]);

  React.useEffect(() => {
    try {
      localStorage.setItem(
        "currentSessionId",
        JSON.stringify(currentSessionId),
      );
    } catch {}
  }, [currentSessionId]);

  React.useEffect(() => {
    try {
      localStorage.setItem("guest", JSON.stringify(guest));
    } catch {}
  }, [guest]);

  React.useEffect(() => {
    const sessions = chatSessions ?? [];

    //  초기 상태는 세션 0개 허용 (아무 것도 만들지 않음)
    if (sessions.length === 0) {
      if (currentSessionId !== null) setCurrentSessionId(null);
      return;
    }

    // currentSessionId가 없거나, 존재하지 않는 id면 첫 세션으로 보정
    const exists = sessions.some((s) => s?.sessionId === currentSessionId);
    if (!currentSessionId || !exists) {
      setCurrentSessionId(sessions[0]?.sessionId ?? null);
    }
  }, [chatSessions, currentSessionId]);

  const isLiked = React.useCallback(
    (item) => (favorites ?? []).some((x) => x.itemKey === item.itemKey),
    [favorites],
  );

  const currentSession = React.useMemo(() => {
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
      const base = prev ?? initialGuest;
      if (base.guestId) return base;
      return { ...base, guestId: genId("g_") };
    });
  }, []);

  const resetGuest = React.useCallback(() => {
    setGuestState(initialGuest);
    try {
      localStorage.setItem("guest", JSON.stringify(initialGuest));
    } catch {}
  }, []);

  const createNewSession = React.useCallback(() => {
    const sessionId = genId();
    const createdAt = Date.now();

    setChatSessions((prev) => {
      const base = prev ?? [];
      const title = getNextSessionTitle(base);
      const newSession = { sessionId, createdAt, title, turns: [] };
      return [newSession, ...base];
    });

    setCurrentSessionId(sessionId);
    return sessionId;
  }, []);

  // 특정 세션에 turn 추가 (세션ID로 직접)
  const appendTurnToSession = React.useCallback((sessionId, turn) => {
    if (!sessionId || !turn) return;
    setChatSessions((prev) =>
      (prev ?? []).map((s) =>
        s.sessionId === sessionId
          ? { ...s, turns: [...(s.turns ?? []), turn] }
          : s,
      ),
    );
  }, []);

  // turnId로 전체 세션 중에서 찾아 업데이트 (currentSessionId에 의존 X)
  const updateTurnById = React.useCallback((turnId, updater) => {
    if (!turnId || typeof updater !== "function") return;

    setChatSessions((prev) =>
      (prev ?? []).map((s) => {
        const turns = s.turns ?? [];
        const idx = turns.findIndex((t) => t?.id === turnId);
        if (idx < 0) return s;

        const nextTurns = [...turns];
        nextTurns[idx] = updater(nextTurns[idx]);
        return { ...s, turns: nextTurns };
      }),
    );
  }, []);

  const selectSession = React.useCallback((sessionId) => {
    setCurrentSessionId(sessionId ?? null);
  }, []);

  const renameSession = React.useCallback((sessionId, title) => {
    const nextTitle = normalizeTitle(title);

    setChatSessions((prev) =>
      (prev ?? []).map((s) =>
        s.sessionId === sessionId ? { ...s, title: nextTitle } : s,
      ),
    );
  }, []);

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
      const base = prev ?? [];
      const exists = base.some((x) => x.itemKey === item.itemKey);
      return exists
        ? base.filter((x) => x.itemKey !== item.itemKey)
        : [{ ...item, likedAt: Date.now() }, ...base];
    });
  }, []);

  const addHistoryTurn = React.useCallback((historyTurn) => {
    setHistory((prev) => [historyTurn, ...(prev ?? [])].slice(0, 50));
  }, []);

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

      // turn actions (핵심)
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
      favorites,
      toggleLike,
      isLiked,
      history,
      addHistoryTurn,
      chatSessions,
      currentSessionId,
      createNewSession,
      appendTurnToSession,
      updateTurnById,
      renameSession,
      deleteSession,
      chatLogs,
      guest,
      setGuest,
      ensureGuestId,
      resetGuest,
    ],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
};

export const useAppData = () => {
  const v = React.useContext(Ctx);
  if (!v) throw new Error("useAppData must be used within AppDataProvider");
  return v;
};
