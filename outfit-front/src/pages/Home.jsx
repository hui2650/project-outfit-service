import React, { useState } from 'react'

import Header from '../components/layout/Header'
import AppShell from '../components/layout/AppShell'
import ResultStage from '../components/stage/ResultStage'
import SidePanel from '../components/panel/sidepanel/SidePanel'

import { useFileInput } from '../hooks/useFileInput'
import { useChatLogs } from '../hooks/useChatLogs'
import { useRecommend } from '../hooks/useRecommend'
import { createTurn } from '../utils/createTurn'
import { useInputOptions } from '../hooks/useInputOptions'

const Home = () => {
<<<<<<< HEAD
  const [file, setFile] = React.useState(null);
  const [previewUrl, setPreviewUrl] = React.useState(null);
  const [textQuery, setTextQuery] = React.useState("");
  const [chatLogs, setChatLogs] = React.useState([]);
  const [items, setItems] = React.useState([]);
  const [requestId, setRequestId] = React.useState(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState(null);
  const [category, setCategory] = React.useState(null);
=======
  const { file, previewUrl, handleFile, setFile } = useFileInput()
  const { chatLogs, appendTurn, updateTurn } = useChatLogs()
  const { requestRecommend } = useRecommend({ updateTurn })
>>>>>>> feature/taehui/default-uI

  const [error, setError] = useState(null)

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
<<<<<<< HEAD
    console.log("SUBMIT", { hasFile: !!file, textQuery, category });
    // (0) 파일이 없으면 업로드 요청 자체를 막음 (프론트 1차 검증)
    //     -> 백엔드 보내봤자 400/에러이므로, 사용자에게 바로 안내하는 UX
=======
>>>>>>> feature/taehui/default-uI
    if (!file) {
      setError({ code: 'NO_FILE', message: '이미지를 업로드해주세요' })
      return
    }

    const newTurn = createTurn({
      file,
      previewUrl,
      textQuery,
      category,
      gender,
    })

    appendTurn(newTurn)

    await requestRecommend({
      turnId: newTurn.id,
      file,
      textQuery,
      category,
      gender,
    })

<<<<<<< HEAD
    // (1) 요청 시작 상태로 전환
    //     -> 버튼 disabled / 로딩 텍스트 표시 등에 사용
    setLoading(true);
    // (2) 이전 에러가 화면에 남아있으면 헷갈리니까 초기화
    setError(null);

    try {
      // (3) 실제 API 호출: Spring으로 multipart 전송(이미지 + limit)
      //     -> await이므로 응답 받을 때까지 이 함수는 여기서 잠시 멈춤
      const resp = await recommendByImage(file, 8, textQuery, category);

      // (4) 응답이 "에러 형태"로 내려온 경우(서버가 JSON으로 에러를 통일해서 준다는 가정)
      //     -> items 렌더 대신 에러 메시지를 렌더하게 됨
      if (resp.error) {
        setError(resp.error); // 에러 state 업데이트
        return; // 성공 처리로 내려가지 않게 여기서 종료
      }

      // ✅ 여기서 “프론트가 쓰는 형태”로 통일하는 게 중요
      // 서버가 { data: { items: [...] } } 같은 형태면 여기서 꺼내주기
      // const receivedItems = resp.items ?? resp.data?.items ?? [];
      // const receivedRequestId = resp.requestId ?? resp.data?.requestId ?? null;
      const receivedItems = resp.items ?? [];
      const receivedRequestId = resp.requestId ?? null;

      // 🧡 응답 오면 output을 turn에 채워넣기
      setChatLogs((prev) =>
        prev.map((t) =>
          t.id === newTurnId
            ? {
                ...t,
                output: {
                  requestId: receivedRequestId,
                  items: receivedItems,
                },
              }
            : t,
        ),
      );

      // (5) 성공 응답이면 requestId 저장 + 추천 items 저장
      //     -> ResultStage(왼쪽)에서 items를 받아 캐러셀 렌더
      // 🧡 최신 결과도 따로 보여주고 싶으면 유지
      setRequestId(receivedRequestId);
      // (6) resp.items
      setItems(receivedItems);

      // 파일, 이미지, 카테고리 초기화
      setFile(null);
      setPreviewUrl(null);
      setCategory(null);
    } catch (e) {
      // (7) fetch 자체 실패(네트워크 끊김, CORS, 서버 다운 등)
      //     -> 서버가 에러 JSON을 준 게 아니라 "요청이 성립하지 않은" 상황
      setError({ code: "NETWORK_ERROR", message: "서버 연결이 불안정해" });

      // (8) 기존 추천 결과를 지움(사용자 혼란 방지)
      setItems([]);
    } finally {
      // (9) 성공/실패 상관없이 로딩 종료
      setLoading(false);
    }
  };
=======
    setFile(null)
    reset()
  }
>>>>>>> feature/taehui/default-uI

  return (
    <>
      <Header />
      <AppShell
        left={<ResultStage chatLogs={chatLogs} />}
        right={
          <SidePanel
            file={file}
            error={error}
            previewUrl={previewUrl}
            onTextQuery={setTextQuery}
<<<<<<< HEAD
            onChangeCategory={setCategory}
=======
            textQuery={textQuery}
            onChangeCategory={setCategory}
            category={category}
            onChangeGender={setGender}
            gender={gender}
>>>>>>> feature/taehui/default-uI
            onFile={handleFile}
            category={category}
            onSubmit={handleSubmit}
          />
        }
      />
    </>
  )
}

export default Home
