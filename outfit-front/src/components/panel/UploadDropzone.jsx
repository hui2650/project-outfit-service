// file input 숨겨두고  클릭/드랍 처리
// 선택된 파일을 상위로 전달 onFile(file)
// previewUrl은 상위에서 만들어 전달받아 표시만함

import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faImage } from '@fortawesome/free-solid-svg-icons'

const UploadDropzone = ({ previewUrl, onFile, inputRef }) => {
  return (
    <div
      className="group relative border border-dashed border-3 rounded-xl h-52 flex items-center justify-center hover:border-primary/70 hover:bg-primary/5 overflow-hidden"
      onClick={() => inputRef.current?.click()}
      onDragOver={(e) => e.preventDefault()}
      onDrop={(e) => {
        // 기본 동작을 막아야 드랍이 “업로드”로 처리되기 때문에 기본 동작 막기
        e.preventDefault()

        // e.dataTransfer = 드래그로 옮겨지는 데이터(텍스트/URL/파일 등)를 담는 객체
        // 파일을 끌어다 놓으면 e.dataTransfer.files에 파일 목록이 들어감
        const f = e.dataTransfer.files?.[0] || null
        onFile(f)
      }}
    >
      {previewUrl ? (
        <img
          src={previewUrl}
          alt="preview"
          className="absolute w-full h-auto"
        />
      ) : (
        <div className="flex flex-col justify-center items-center">
          <div className="mb-6">
            <FontAwesomeIcon
              icon={faImage}
              className=" text-4xl px-3.5 py-4 rounded-[24px] transition-colors
             text-primary/80 bg-primary/15
             group-hover:bg-primary/25
             group-hover:text-primary/90"
            />
          </div>
          <div className="text-foreground/80 text-xs md:text-sm text-center px-6">
            이미지를 드래그하거나
            <br />
            클릭해서 업로드하세요
          </div>
        </div>
      )}

      {/* 숨김처리 */}
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={(e) => onFile(e.target.files?.[0] || null)}
      />
    </div>
  )
}

export default UploadDropzone
