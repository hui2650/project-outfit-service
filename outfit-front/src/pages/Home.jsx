import React, { useRef, useState } from 'react'
import AppShell from '../components/layout/AppShell'
import ResultStage from '../components/stage/ResultStage'
import SidePanel from '../components/panel/sidepanel/SidePanel'
import { useFileInput } from '../hooks/useFileInput'
import { useChatLogs } from '../hooks/useChatLogs'
import { useRecommend } from '../hooks/useRecommend'
import { createTurn } from '../utils/createTurn'
import { useInputOptions } from '../hooks/useInputOptions'
import { useAppData } from '../store/appDataStore.jsx'
import { useFollowupChat } from '../hooks/useFollowupChat'

const Home = () => {
  const { file, previewUrl, handleFile, clear } = useFileInput()
  const { chatLogs, appendTurn, updateTurn } = useChatLogs()
  const { addHistoryTurn } = useAppData()
  const { requestRecommend } = useRecommend({
    updateTurn,
    onHistoryTurn: addHistoryTurn,
  })
  const [error, setError] = useState(null)

  const inputRef = useRef(null)

  const {
    textQuery,
    setTextQuery,
    category,
    setCategory,
    gender,
    setGender,
    reset,
  } = useInputOptions()

  const handleSubmit = async () => {
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

    try {
      await requestRecommend({
        turnId: newTurn.id,
        file,
        textQuery,
        category,
        gender,
      })

      // 성공했을 때만 초기화
      clear()
      if (inputRef.current) inputRef.current.value = ''
      reset()
    } catch (e) {
      // 실패면 이미지/옵션 유지 (재시도 UX)
      // 필요하면 setError로 메시지 세팅
    }
  }

  const { sendChat } = useFollowupChat({ updateTurn })

  const latestDoneTurn = React.useMemo(() => {
    // 가장 최근 done 찾기
    for (let i = chatLogs.length - 1; i >= 0; i--) {
      if (chatLogs[i].status === 'done') return chatLogs[i]
    }
    return null
  }, [chatLogs])

  const chatDisabled = !latestDoneTurn

  const handleSendChat = async (text) => {
    if (!latestDoneTurn) return

    // 이 turn에 붙일 컨텍스트: requestId, items, category/gender(있으면)
    const requestId = latestDoneTurn.requestId ?? null

    // carousel 메시지에서 items 뽑기 (없으면 빈 배열)
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
  }

  return (
    <>
      <AppShell
        left={
          <ResultStage
            chatLogs={chatLogs}
            onSendChat={handleSendChat}
            chatDisabled={chatDisabled}
          />
        }
        right={
          <SidePanel
            file={file}
            error={error}
            previewUrl={previewUrl}
            inputRef={inputRef}
            onTextQuery={setTextQuery}
            textQuery={textQuery}
            onChangeCategory={setCategory}
            category={category}
            onChangeGender={setGender}
            gender={gender}
            onFile={handleFile}
            onSubmit={handleSubmit}
          />
        }
      />
    </>
  )
}
export default Home
