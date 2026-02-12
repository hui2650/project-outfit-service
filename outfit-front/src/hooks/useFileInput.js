import { useEffect, useState } from "react";

/**
 * useFileInput()
 * - "파일 업로드 + 미리보기 URL 관리"를 전담하는 훅
 *
 * 핵심:
 * - createObjectURL로 만든 blob URL은
 *   1) previewUrl이 바뀌기 직전
 *   2) 컴포넌트 언마운트 시
 *   useEffect cleanup에서 revoke 해준다.
 *
 * - clear()에서 즉시 revoke하면 "제출 직후"에도 img가 blob을 읽어야 하는데
 *   바로 끊겨서 ERR_FILE_NOT_FOUND가 날 수 있다.
 */
export const useFileInput = () => {
  // 서버로 보낼 파일 원본
  const [file, setFile] = useState(null);

  // 화면 미리보기용 blob URL
  const [previewUrl, setPreviewUrl] = useState(null);

  const handleFile = (f) => {
    setFile(f);

    // 사용자가 파일을 취소하거나 제거한 경우
    if (!f) {
      setPreviewUrl(null);
      return;
    }

    // 새 파일을 미리보기로 보여주기 위한 blob URL 생성
    setPreviewUrl(URL.createObjectURL(f));
  };

  // ✅ IMPORTANT: 여기서 revoke를 "즉시" 하지 않는다.
  // 이유: submit 직후에도 chat/preview에서 blob을 렌더링할 수 있음
  const clear = () => {
    setFile(null);
    setPreviewUrl(null);
  };

  // ✅ revoke는 여기서 책임진다:
  // - previewUrl이 변경되기 직전 이전 previewUrl revoke
  // - 컴포넌트 언마운트 시 revoke
  useEffect(() => {
    if (!previewUrl) return;

    return () => {
      URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  return {
    file,
    previewUrl,
    setFile,
    handleFile,
    clear,
  };
};
