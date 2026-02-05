// 1) 업로드
// UploadDropzone에서 file 선택 → onFile(file) 호출
// → App이 file 저장 + previewUrl 생성

// 2) 추천받기
// SubmitButton 클릭 → App의 handleSubmit()
// file 없으면 error 세팅
// 있으면 loading true
// API 호출 → items 세팅 + requestId 세팅
// loading false


import "./App.css";
import Home from "./pages/Home";

function App() {
  return (
    <>
      <Home />
    </>
  );
}

export default App;
