import React from 'react'
import UploadDropzone from '../UploadDropzone'
import GenderChoice from '../GenderChoice'
import CategoryChoice from '../CategoryChoice'
import TextQueryBox from '../TextQueryBox'
import SubmitButton from '../SubmitButton'
import { useChatPage } from '../../../pages/chat/ChatPageContext.jsx' // 경로 맞춰

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

  const pickFile = () => inputRef.current?.click()

  return (
    <div className="h-full bg-card/90 px-4 py-6 lg:p-8 flex-1 overflow-y-auto scrollbar-nice">
      <UploadDropzone
        previewUrl={previewUrl}
        onFile={handleFile}
        inputRef={inputRef}
      />

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
        isReadyToSubmit={!!file && !!category && !!gender}
      />
    </div>
  )
}

export default SidePanelContent
