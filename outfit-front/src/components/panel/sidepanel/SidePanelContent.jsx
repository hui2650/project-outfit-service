import React from 'react'
import UploadDropzone from '../UploadDropzone'
import GenderChoice from '../GenderChoice'
import CategoryChoice from '../CategoryChoice'
import TextQueryBox from '../TextQueryBox'
import SubmitButton from '../SubmitButton'
import { useChatPage } from '../../../pages/chat/ChatPageContext.jsx' // 경로 맞춰

/*
SidePanelContent
- 아이템 입력의 핵심 폼 영역
- 상태/핸들러는 ChatPageContext에서 가져와서 "입력 → submit" 플로우를 한 곳에서 관리
- file/category/gender가 모두 있어야 제출 버튼 활성화
*/

const SidePanelContent = ({ loading }) => {
  const {
    previewUrl,
    inputRef,
    textQuery,
    setTextQuery,
    handleFile,
    handleSubmit,
    setCategory,
    category,
    gender,
    setGender,
    file,
  } = useChatPage()

  // file input은 숨겨두고, 외부 버튼 클릭으로 input 클릭을 트리거
  const pickFile = () => inputRef.current?.click()

  return (
    /*
    스크롤 컨텐츠 영역
    - 모바일/데스크톱에서 동일하게 내부 스크롤이 생기도록 overflow-y-auto
    - 배경을 살짝 투명 처리해 레이어 느낌을 유지
    */
    <div className="h-full bg-card/90 px-4 py-6 lg:p-8 flex-1 overflow-y-auto scrollbar-nice">
      <UploadDropzone
        previewUrl={previewUrl}
        onFile={handleFile}
        inputRef={inputRef}
      />

      {/* 드랍존 외에도 명시적인 파일 선택 버튼 제공 */}
      <button
        className="mt-4 w-full rounded-xl 
        bg-gradient-to-r from-primary/90 to-accent/90
        text-white text-sm md:text-base
        py-3 font-semibold
        hover:opacity-90
        transition
        shadow-[0_4px_14px_rgba(124,58,237,0.15)]
        "
        type="button"
        onClick={pickFile}
      >
        이미지 선택
      </button>

      <GenderChoice gender={gender} onChangeGender={setGender} />
      <hr />
      <CategoryChoice category={category} onChangeCategory={setCategory} />
      <TextQueryBox textQuery={textQuery} onTextQuery={setTextQuery} />

      <SubmitButton
        loading={loading}
        onSubmit={handleSubmit}
        // 필수 입력이 모두 채워졌을 때만 제출 가능
        isReadyToSubmit={!!file && !!category && !!gender}
      />
    </div>
  )
}

export default SidePanelContent
