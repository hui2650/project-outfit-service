// 오른쪽 영역
// 업로드, 텍스트, 제출 버튼을 모아서 배치

import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faImage } from "@fortawesome/free-solid-svg-icons";

import UploadDropzone from "./UploadDropzone";
import TextQueryBox from "./TextQueryBox";
import SubmitButton from "./SubmitButton";
import React from "react";
import CategoryChoice from "./CategoryChoice";

const SidePanel = ({
  previewUrl,
  textQuery,
  onTextQuery,
  onFile,
  onSubmit,
  loading,
  onChangeCategory,
  category,
  file,
}) => {
  const inputRef = React.useRef(null);

  // Dropzone 내부 클릭하면 파일 선택창 열기
  const pickFile = () => inputRef.current?.click();

  return (
    <div className="relative flex flex-col justify-between h-full shrink-0 shadow-lg max-w-sm z-10">
      <div className="p-5 bg-white shrink-0 border-b ">
        <div className="flex itmes-center gap-2">
          <FontAwesomeIcon
            icon={faImage}
            style={{
              color: "hsl(270, 70%, 60%)",
              background: "hsl(270, 80%, 92%)",
              borderRadius: "12px",
            }}
            className=" text-lg px-1.5 py-2 overflow-hidden"
          />
          <h2 className="font-foreground font-semibold text-base leading-loose">
            아이템 입력
          </h2>
        </div>
      </div>
      <div className="p-8 flex-1 overflow-y-auto">
        <UploadDropzone
          previewUrl={previewUrl}
          onFile={onFile}
          inputRef={inputRef}
        />

        {/* 버튼은 그냥 실행만 */}
        <button
          className="mt-4 w-full rounded-xl bg-primary text-primary-foreground py-3 font-semibold"
          type="button"
          onClick={pickFile}
        >
          이미지 선택
        </button>
        <CategoryChoice
          category={category}
          onChangeCategory={onChangeCategory}
        />
        <TextQueryBox textQuery={textQuery} onTextQuery={onTextQuery} />

        <SubmitButton
          loading={loading}
          onSubmit={onSubmit}
          isReadyToSubmit={!!file && !!category} //!!file: 파일이 존재하면 true, 선택된 카테고리가 있다면 true 둘 다 있어야 버튼이 활성화됨
        />
      </div>

      <div className="p-6 w-full bg-white shrink-0 border-t ">
        <h2 className="text-sm">게스트 사용자</h2>
        <span className="text-xs">로그인하여 저장하기</span>
      </div>

      <div className="p-6 w-full bg-white shrink-0 border-t ">
        <h2 className="text-sm">게스트 사용자</h2>
        <span className="text-xs">로그인하여 저장하기</span>
      </div>
    </div>
  );
};

export default SidePanel;
