import React from "react";
import { useAppData } from "../store/appDataStore.jsx";

export const useChatLogs = () => {
  const { chatLogs, setChatSessions, currentSessionId } = useAppData();

  const appendTurn = React.useCallback(
    (turn) => {
      setChatSessions((prev) =>
        prev.map((session) =>
          session.sessionId === currentSessionId
            ? { ...session, turns: [...session.turns, turn] }
            : session,
        ),
      );
    },
    [setChatSessions, currentSessionId],
  );

  const updateTurn = React.useCallback(
    (turnId, updater) => {
      setChatSessions((prev) =>
        prev.map((session) => {
          if (session.sessionId !== currentSessionId) return session;

          return {
            ...session,
            turns: session.turns.map((t) => (t.id === turnId ? updater(t) : t)),
          };
        }),
      );
    },
    [setChatSessions, currentSessionId],
  );

  return { chatLogs, appendTurn, updateTurn };
};
