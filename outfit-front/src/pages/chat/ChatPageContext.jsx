import React from 'react'
import { useFileInput } from '../../hooks/useFileInput'
import { useChatLogs } from '../../hooks/useChatLogs'
import { useRecommend } from '../../hooks/useRecommend'
import { useInputOptions } from '../../hooks/useInputOptions'
import { useAppData } from '../../store/appDataStore.jsx'
import { useFollowupChat } from '../../hooks/useFollowupChat'
import { createTurn } from '../../utils/createTurn'

const ChatPageCtx = React.createContext(null)

export const ChatPageProvider = ({ children }) => {
  // ===============================
  // 1) right panel mode
  // ===============================
  const [rightPanelMode, setRightPanelMode] = React.useState('input') // "input" | "sessions"
  //  중복 요청 방지 락
  const submitLockRef = React.useRef(false)
  const openInputPanel = React.useCallback(() => setRightPanelMode('input'), [])
  const openSessionsPanel = React.useCallback(
    () => setRightPanelMode('sessions'),
    []
  )

  // ===============================
  // 2) input states
  // ===============================
  const { file, previewUrl, handleFile, clear } = useFileInput()
  const inputRef = React.useRef(null)

  const {
    textQuery,
    setTextQuery,
    category,
    setCategory,
    gender,
    setGender,
    reset,
  } = useInputOptions()

  const [error, setError] = React.useState(null)

  // ===============================
  // 3) chat logs + session
  // ===============================
  const { chatLogs, appendTurn, updateTurn } = useChatLogs()
  const { addHistoryTurn, createNewSession } = useAppData()
  const { requestRecommend } = useRecommend({
    updateTurn,
    onHistoryTurn: addHistoryTurn,
  })

  const { sendChat } = useFollowupChat({ updateTurn })

  // ===============================
  // 4) derived
  // ===============================
  const latestDoneTurn = React.useMemo(() => {
    if (!Array.isArray(chatLogs)) return null
    for (let i = chatLogs.length - 1; i >= 0; i--) {
      if (chatLogs[i].status === 'done') return chatLogs[i]
    }
    return null
  }, [chatLogs])

  const chatDisabled = !latestDoneTurn

  // ===============================
  // 5) handlers
  // ===============================
  const resetRightInputs = React.useCallback(() => {
    setError(null)
    clear()
    if (inputRef.current) inputRef.current.value = ''
    reset()
  }, [clear, reset])

  const handleNewChat = React.useCallback(() => {
    createNewSession()
    resetRightInputs()
    openInputPanel() // 새 채팅은 무조건 input으로
  }, [createNewSession, resetRightInputs, openInputPanel])

  const handleSubmit = React.useCallback(async () => {
    // 이미 요청중이면 무시
    if (submitLockRef.current) return

    if (!file) {
      setError({ code: 'NO_FILE', message: '이미지를 업로드해주세요' })
      return
    }

    setError(null)

    const newTurn = createTurn({
      file,
      previewUrl,
      textQuery,
      category,
      gender,
    })

    appendTurn(newTurn)

    // 락
    submitLockRef.current = true

    try {
      await requestRecommend({
        turnId: newTurn.id,
        file,
        textQuery,
        category,
        gender,
      })

      // 성공했을 때만 초기화
      resetRightInputs()
    } catch (e) {
      // 실패면 유지(재시도 UX)
    } finally {
      //  무조건 락 OFF
      submitLockRef.current = false
    }
  }, [
    file,
    previewUrl,
    textQuery,
    category,
    gender,
    appendTurn,
    requestRecommend,
    resetRightInputs,
  ])

  const handleSendChat = React.useCallback(
    async (text) => {
      if (!latestDoneTurn) return

      const requestId = latestDoneTurn.requestId ?? null
      const carouselMsg = [...latestDoneTurn.messages]
        .reverse()
        .find((m) => m.type === 'carousel')
      const items = carouselMsg?.items ?? []

      await sendChat({
        turnId: latestDoneTurn.id,
        text,
        requestId,
        items,
        category,
        gender,
      })
    },
    [latestDoneTurn, sendChat, category, gender]
  )

  const value = React.useMemo(
    () => ({
      // panel mode
      rightPanelMode,
      openInputPanel,
      openSessionsPanel,

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
      chatLogs,
      chatDisabled,

      // actions
      handleSubmit,
      handleNewChat,
      handleSendChat,

      // for session panel
      setRightPanelMode, // (필요하면)
    }),
    [
      rightPanelMode,
      openInputPanel,
      openSessionsPanel,
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
      chatDisabled,
      handleSubmit,
      handleNewChat,
      handleSendChat,
    ]
  )

  return <ChatPageCtx.Provider value={value}>{children}</ChatPageCtx.Provider>
}

export const useChatPage = () => {
  const v = React.useContext(ChatPageCtx)
  if (!v) throw new Error('useChatPage must be used within ChatPageProvider')
  return v
}
