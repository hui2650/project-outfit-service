/**
 * recommendByImage()
 *
 * 역할
 * - 이미지 기반 추천 API 호출
 * - FormData로 파일 + 옵션을 서버에 전달
 *
 * 서버 계약 포인트
 * - "image": UploadFile
 * - "limit", "textQuery", "category", "gender": Form field
 * - guestId/nickname/style도 Form field로 전달
 *
 * 반환값
 * - 성공: data (보통 { items: [...], requestId, ... } 형태)
 * - 실패:
 *   1) 서버가 { error: { message, code } } 형태로 JSON을 주면 그걸 그대로 반환
 *   2) JSON이 아니면 Error throw
 */
export async function recommendByImage(
  file,
  limit = 8,
  textQuery = '',
  category = '',
  gender = '',
  guestId = '',
  nickname = '',
  style = ''
) {
  const form = new FormData()

  // 업로드 파일 (FastAPI에서 UploadFile로 받는 필드명)
  form.append('image', file)

  // 옵션들(Form field)
  form.append('limit', String(limit))
  form.append('textQuery', textQuery)
  form.append('category', category)
  form.append('gender', gender)

  // 게스트 사용자 정보(Form field)
  form.append('guestId', guestId ?? '')
  form.append('nickname', nickname ?? '')
  form.append('style', style ?? '')

  /**
   * fetch 경로
   * - "/api/v1/recommend/image"
   * - 개발 환경에서 프론트 프록시 또는 백엔드 gateway가 받아서 FastAPI로 전달하는 구조
   */
  const res = await fetch('/api/v1/recommend/image', {
    method: 'POST',
    body: form,
  })

  // 에러 상황에서도 서버 응답을 최대한 회수하려고 시도
  let data = null
  let text = ''

  // 1순위: JSON 파싱 시도
  try {
    data = await res.json()
  } catch {
    // JSON이 아니면 text로 회수 (서버가 HTML/텍스트 에러를 주는 경우)
    text = await res.text().catch(() => '')
  }

  /**
   * HTTP 상태 코드 기준 실패 처리
   * - 서버가 error JSON을 줬으면 그대로 반환해 UI에서 메시지 표출 가능
   * - 아니면 예외로 던져서 상위에서 공통 에러 처리
   */
  if (!res.ok) {
    console.error('[recommendByImage] HTTP', res.status, data ?? text)
    if (data?.error) return data
    throw new Error(`HTTP_${res.status}`)
  }

  return data
}
