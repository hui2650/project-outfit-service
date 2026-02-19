import React from "react";
import { useFileInput } from "../../hooks/useFileInput";
import { useRecommend } from "../../hooks/useRecommend";
import { useInputOptions } from "../../hooks/useInputOptions";
import { useAppData } from "../../store/appDataStore.jsx";
import { useFollowupChat } from "../../hooks/useFollowupChat";
import { createTurn } from "../../utils/createTurn";

const ChatPageCtx = React.createContext(null);

export const ChatPageProvider = ({ children }) => {
  // ===============================
  // 1) right panel mode
  // ===============================
  const [rightPanelMode, setRightPanelMode] = React.useState("input"); // "input" | "sessions"

  const [maskLogsAsEmpty, setMaskLogsAsEmpty] = React.useState(false);

  const [emptyReloadKey, setEmptyReloadKey] = React.useState(0);

  // 중복 요청 방지 락
  const submitLockRef = React.useRef(false);

  const openInputPanel = React.useCallback(
    () => setRightPanelMode("input"),
    [],
  );

  const openSessionsPanel = React.useCallback(
    () => setRightPanelMode("sessions"),
    [],
  );

  const triggerEmptyReload = React.useCallback(() => {
    setEmptyReloadKey((prev) => prev + 1);
  }, []);

  // ===============================
  // 2) input states
  // ===============================
  const { file, previewUrl, handleFile, clear, freezePreview } = useFileInput();
  const inputRef = React.useRef(null);

  const {
    textQuery,
    setTextQuery,
    category,
    setCategory,
    gender,
    setGender,
    reset,
  } = useInputOptions();

  const [error, setError] = React.useState(null);

  // ===============================
  // 3) chat logs session
  // ===============================
  const {
    chatLogs,
    currentSessionId,
    addHistoryTurn,
    createNewSession,
    appendTurnToSession,
    updateTurnById,
  } = useAppData();

  // useRecommend / useFollowupChat 에는 updateTurn 함수가 필요하므로 updateTurnById를 그대로 넘김
  const updateTurn = updateTurnById;

  const { requestRecommend } = useRecommend({
    updateTurn,
    onHistoryTurn: addHistoryTurn,
  });

  const { sendChat } = useFollowupChat({ updateTurn });

  // ===============================
  // 4) derived
  // ===============================
  const effectiveChatLogs = React.useMemo(() => {
    return maskLogsAsEmpty ? [] : chatLogs;
  }, [maskLogsAsEmpty, chatLogs]);

  const latestDoneTurn = React.useMemo(() => {
    if (!Array.isArray(effectiveChatLogs)) return null;
    for (let i = effectiveChatLogs.length - 1; i >= 0; i--) {
      if (effectiveChatLogs[i]?.status === "done") return effectiveChatLogs[i];
    }
    return null;
  }, [effectiveChatLogs]);

  const chatDisabled = !latestDoneTurn;

  // ===============================
  // 5) handlers
  // ===============================
  const resetRightInputs = React.useCallback(() => {
    setError(null);
    clear();
    if (inputRef.current) inputRef.current.value = "";
    reset();
  }, [clear, reset]);

  const handleNewChat = React.useCallback(() => {
    createNewSession();
    resetRightInputs();
  }, [createNewSession, resetRightInputs, openInputPanel]);

  const handleSubmit = React.useCallback(async () => {
    // 이미 요청중이면 무시
    if (submitLockRef.current) return;

    if (!file) {
      setError({ code: "NO_FILE", message: "이미지를 업로드해주세요" });
      return;
    }

    setError(null);
    const sentUrl = freezePreview();

    const newTurn = createTurn({
      file,
      previewUrl: sentUrl ?? previewUrl,
      textQuery,
      category,
      gender,
    });

    // targetSessionId를 확정하고 그 세션에 turn을 직접 넣는다 (레이스 제거)
    // createNewSession()이 currentSessionId를 바꾸지만 state 반영은 렌더 후.
    // 그래서 "방금 만든 세션"에 바로 넣기 위해: id를 createNewSession 안에서 만들고 반환하도록 바꾸는 게 이상적.
    // 현재 store의 createNewSession은 내부에서 genId()로 만들기 때문에 여기서 알 수 없으니,
    // 아래 방식으로 바꿔야 한다: createNewSession이 sessionId를 return 하게.

    // ⚠️ 그래서 최종은 createNewSession이 sessionId를 return하도록 store에서 바꿔야 함.
    // 아래는 그 return을 받는 코드:
    let targetSessionId = currentSessionId;

    // 초기 상태(세션 0개)거나, 새로고침 마스크 상태면: 이때만 새 세션 생성
    if (!targetSessionId || maskLogsAsEmpty) {
      targetSessionId = createNewSession();
      setMaskLogsAsEmpty(false);
    }
    appendTurnToSession(targetSessionId, newTurn);

    submitLockRef.current = true;

    try {
      await requestRecommend({
        turnId: newTurn.id,
        file,
        textQuery,
        category,
        gender,
      });

      resetRightInputs();
    } finally {
      submitLockRef.current = false;
    }
  }, [
    file,
    previewUrl,
    textQuery,
    category,
    gender,
    requestRecommend,
    resetRightInputs,
    freezePreview,
    maskLogsAsEmpty,
    createNewSession,
    setMaskLogsAsEmpty,
    currentSessionId,
    appendTurnToSession,
  ]);

  const handleSendChat = React.useCallback(
    async (text) => {
      if (!latestDoneTurn) return;

      const requestId = latestDoneTurn.requestId ?? null;
      const carouselMsg = [...(latestDoneTurn.messages ?? [])]
        .reverse()
        .find((m) => m?.type === "carousel");

      const items = carouselMsg?.items ?? [];

      await sendChat({
        turnId: latestDoneTurn.id,
        text,
        requestId,
        items,
        category,
        gender,
        messages: latestDoneTurn.messages,
      });
    },
    [latestDoneTurn, sendChat, category, gender],
  );

  const didAutoNewSessionRef = React.useRef(false);

  React.useEffect(() => {
    if (!Array.isArray(chatLogs) || chatLogs.length === 0) return;

    const hasLoading = chatLogs.some((t) => t?.status === "loading");
    const hasDone = chatLogs.some((t) => t?.status === "done");

    // 로딩만 있고 done이 없으면: 세션 만들지 말고, 오른쪽 입력만 정리
    if (hasLoading && !hasDone) {
      if (didAutoNewSessionRef.current) return;
      didAutoNewSessionRef.current = true;

      resetRightInputs();
    }
  }, [chatLogs, createNewSession, resetRightInputs, openInputPanel]);

  const value = React.useMemo(
    () => ({
      // panel mode
      rightPanelMode,
      openInputPanel,
      openSessionsPanel,

      triggerEmptyReload,
      emptyReloadKey,

      // right input states
      file,
      previewUrl,
      handleFile,
      inputRef,

      textQuery,
      setTextQuery,
      category,
      setCategory,
      gender,
      setGender,
      error,

      // chat area
      chatLogs: effectiveChatLogs,
      chatDisabled,

      // actions
      handleSubmit,
      handleNewChat,
      handleSendChat,

      // for session panel
      setRightPanelMode,
    }),
    [
      rightPanelMode,
      openInputPanel,
      openSessionsPanel,
      triggerEmptyReload,
      emptyReloadKey,
      file,
      previewUrl,
      handleFile,
      textQuery,
      setTextQuery,
      category,
      setCategory,
      gender,
      setGender,
      error,
      chatLogs,
      effectiveChatLogs,
      chatDisabled,
      handleSubmit,
      handleNewChat,
      handleSendChat,
    ],
  );

  return <ChatPageCtx.Provider value={value}>{children}</ChatPageCtx.Provider>;
};

export const useChatPage = () => {
  const v = React.useContext(ChatPageCtx);
  if (!v) throw new Error("useChatPage must be used within ChatPageProvider");
  return v;
};
