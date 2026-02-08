import React from 'react'
import UploadDropzone from '../UploadDropzone'
import GenderChoice from '../GenderChoice'
import CategoryChoice from '../CategoryChoice'
import TextQueryBox from '../TextQueryBox'
import SubmitButton from '../SubmitButton'

const SidePanelContent = ({
  previewUrl,
  textQuery,
  onTextQuery,
  onFile,
  onSubmit,
  loading,
  onChangeCategory,
  category,
  gender,
  onChangeGender,
  file,
}) => {
  const inputRef = React.useRef(null)
  const pickFile = () => inputRef.current?.click()

  return (
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
      <GenderChoice gender={gender} onChangeGender={onChangeGender} />
      <hr />
      <CategoryChoice category={category} onChangeCategory={onChangeCategory} />
      <TextQueryBox textQuery={textQuery} onTextQuery={onTextQuery} />

      <SubmitButton
        loading={loading}
        onSubmit={onSubmit}
        isReadyToSubmit={!!file && !!category && !!gender} //!!file: 파일이 존재하면 true, 선택된 카테고리가 있다면 true 둘 다 있어야 버튼이 활성화됨
      />
    </div>
  )
}

export default SidePanelContent
