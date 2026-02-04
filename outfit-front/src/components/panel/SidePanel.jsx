// 오른쪽 영역
// 업로드, 텍스트, 제출 버튼을 모아서 배치

import UploadDropzone from "./UploadDropzone";
import TextQueryBox from "./TextQueryBox";
import SubmitButton from "./SubmitButton";
import React from "react";

const SidePanel = ({
  previewUrl,
  textQuery,
  onTextQuery,
  onFile,
  onSubmit,
  loading,
}) => {
  const inputRef = React.useRef(null);

  // Dropzone 내부 클릭하면 파일 선택창 열기
  const pickFile = () => inputRef.current?.click();

  return (
    <div className="relative flex flex-col justify-between h-full shrink-0 shadow">
      <div className="p-8 bg-white shrink-0 border-b ">
        <h1>아이템 입력</h1>
        <h3>사진 또는 텍스트</h3>
      </div>
      <div className="p-8 flex-1 overflow-y-auto">
        <UploadDropzone
          previewUrl={previewUrl}
          onFile={onFile}
          inputRef={inputRef}
        />

        {/* 버튼은 그냥 실행만 */}
        <button
          className="mt-4 w-full rounded-xl bg-violet-600 text-white py-3 font-semibold"
          type="button"
          onClick={pickFile}
        >
          이미지 선택
        </button>
        <hr />
        <TextQueryBox textQuery={textQuery} onTextQuery={onTextQuery} />
      </div>
      <div className="p-8 w-full bg-white shrink-0 border-t ">
        <SubmitButton loading={loading} onSubmit={onSubmit} />
      </div>
    </div>
  );
};

export default SidePanel;
