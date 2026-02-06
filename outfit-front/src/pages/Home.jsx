// 상태 7개
// handleFileSelect, handleSubmit 이벤트 로직

// items를 ResultStage로 내려줌
// file/previewUrl/error/loading 등을 SidePanel에 내려줌

import React from "react";
import AppShell from "../components/layout/AppShell";
import Header from "../components/layout/Header";
import ResultStage from "../components/stage/ResultStage";
import SidePanel from "../components/panel/SidePanel";
import { recommendByImage } from "../api/recommend";

const Home = () => {
  const [file, setFile] = React.useState(null);
  const [previewUrl, setPreviewUrl] = React.useState(null);
  const [textQuery, setTextQuery] = React.useState("");
  const [chatLogs, setChatLogs] = React.useState([]);
  const [items, setItems] = React.useState([]);
  const [requestId, setRequestId] = React.useState(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState(null);
  const [category, setCategory] = React.useState(null);

  // 파일 선택/드랍 처리
  const handleFile = (f) => {
    console.log("HANDLE_FILE", f);
    // 1) 사용자가 선택한 파일(File 객체)을 상태로 저장
    //   -> 나중에 서버로 업로드할 때 FormData에 넣기 위해 필요
    // = “업로드할 파일을 잡아두기”
    setFile(f);

    // 2) 파일을 새로 선택하면 기존 에러 메시지는 일단 지움
    //   -> "파일 없음" 같은 에러가 있었으면 업로드 시도 전 초기화
    setError(null);

    // 3) f가 null이면 (사용자가 파일 선택 취소했거나, 파일 제거 버튼 눌렀거나)
    //    미리보기 URL도 없애고 종료
    if (!f) {
      setPreviewUrl(null);
      return;
    }

    // 5) 선택된 파일 f로 "브라우저가 접근 가능한 임시 URL"을 생성
    //   -> 이 URL을 <img src="...">에 넣으면 로컬 파일이 화면에 미리보기로 뜸
    //   -> 예: blob:http://localhost:5173/3f5c... 같은 형태
    // = “미리보기할 URL 만들기”  = <img src={previewUrl}>
    setPreviewUrl(URL.createObjectURL(f));
  };

  // previewUrl 메모리 정리
  React.useEffect(() => {
    // previewUrl이 바뀌거나, 컴포넌트가 사라질 때 실행되는 정리 함수
    // previewUrl이 바뀌기 직전에 이전 값으로 cleanup 실행
    // 컴포넌트가 unmount(화면에서 사라짐) 될 때 cleanup 실행
    return () => {
      // 기존 previewUrl이 있으면 "그 URL이 잡고 있던 브라우저 메모리/리소스"를 해제
      //   -> createObjectURL은 브라우저 내부에 임시 URL/메모리를 할당하므로, 새 파일로 바뀔 때 이전 걸 revokeObjectURL로 정리해줘야 누수가 줄어듦
      // = 전에 만들었던 blob URL을 “이제 안 쓸게”라고 브라우저에 알리기
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  // 서버 요청
  const handleSubmit = async () => {
    console.log("SUBMIT", { hasFile: !!file, textQuery, category });
    // (0) 파일이 없으면 업로드 요청 자체를 막음 (프론트 1차 검증)
    //     -> 백엔드 보내봤자 400/에러이므로, 사용자에게 바로 안내하는 UX
    if (!file) {
      setError({ code: "NO_FILE", message: "이미지를 업로드해주세요" });
      return; // 아래 API 호출 로직 실행 안 함
    }

    // 🧡 Turn Id 먼저 생성
    const newTurnId = "turn_" + Date.now();

    // 🧡 Turn 객체 생성 (유저 입력 로그)
    const newTurn = {
      id: newTurnId,
      input: {
        previewUrl, // 사용자가 올린 이미지 미리보기
        textQuery, // 사용자가 입력한 텍스트
      },
      output: null, // 아직 결과 없음
    };

    // 🧡 요청 시작과 동시에 chatLogs에 추가
    // -> 이 순간 Stage가 자동으로 아래로 내려감
    setChatLogs((prev) => [...prev, newTurn]);

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

  return (
    <>
      <Header />
      <AppShell
        left={
          <ResultStage
            items={items}
            requestId={requestId}
            loading={loading}
            textQuery={textQuery}
            previewUrl={previewUrl}
            chatLogs={chatLogs}
          />
        }
        right={
          <SidePanel
            file={file}
            previewUrl={previewUrl}
            textQuery={textQuery}
            onTextQuery={setTextQuery}
            onChangeCategory={setCategory}
            onFile={handleFile}
            category={category}
            onSubmit={handleSubmit}
            loading={loading}
            error={error}
          />
        }
      />
    </>
  );
};

export default Home;
