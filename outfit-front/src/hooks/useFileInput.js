import { useEffect, useState } from "react";

/**
 * useFileInput()
 * - "파일 업로드 + 미리보기 URL 관리"를 전담하는 훅
 *
 * 이 훅이 해결하는 문제
 * 1) <input type="file">로 받은 File 객체를 상태로 보관
 * 2) 업로드한 파일을 화면에 미리보기로 보여주기 위해 blob URL 생성
 * 3) blob URL은 브라우저 메모리를 잡아먹으므로 "해제(revoke)"까지 책임
 *
 * 반환값
 * - file: 서버로 전송할 원본 File 객체
 * - previewUrl: 화면에 <img src={previewUrl}>로 뿌릴 blob URL
 * - setFile: file을 직접 제어해야 하는 경우(제출 후 초기화 등)
 * - handleFile: 파일 선택/드랍 시 호출하는 핸들러(표준 진입점)
 */
export const useFileInput = () => {
  // 서버로 보낼 파일 원본
  const [file, setFile] = useState(null);

  // 화면 미리보기용 blob URL
  const [previewUrl, setPreviewUrl] = useState(null);

  // 전송 후에도 유지되는 미리보기(썸네일) URL
  const [sentPreviewUrl, setSentPreviewUrl] = useState(null);

  const freezePreview = () => {
    if (!file) return null;
    const url = URL.createObjectURL(file);
    setSentPreviewUrl(url);
    return url;
  };

  /**
   * handleFile(f)
   * - Dropzone / input change 등에서 받은 File을 처리
   *
   * 동작 흐름
   * 1) file state에 File 객체 저장
   * 2) 파일이 없다면 previewUrl 제거
   * 3) 파일이 있다면 URL.createObjectURL로 blob URL 생성 후 previewUrl 저장
   *
   * ⚠️ 중요한 포인트
   * - URL.createObjectURL은 "브라우저 메모리/리소스"를 할당한다
   * - 따라서 previewUrl이 바뀌거나 컴포넌트가 언마운트 될 때 revoke가 필요하다
   */
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

  const clear = () => {
    setFile(null);
    setPreviewUrl(null);
  };

  /**
   * previewUrl cleanup
   *
   * 언제 실행?
   * - previewUrl이 변경되기 "직전"에 이전 previewUrl을 revoke
   * - 컴포넌트가 언마운트 될 때 revoke
   *
   * 왜 필요?
   * - revoke를 안 하면 파일을 계속 바꿀 때 blob URL이 누수처럼 쌓일 수 있음
   */
  useEffect(() => {
    if (!previewUrl) return;

    return () => {
      URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  useEffect(() => {
    if (!sentPreviewUrl) return;
    return () => URL.revokeObjectURL(sentPreviewUrl);
  }, [sentPreviewUrl]);

  return {
    file,
    previewUrl,
    setFile,
    handleFile,
    clear,
    sentPreviewUrl,
    freezePreview,
    // setSentPreviewUrl,
  };
};
