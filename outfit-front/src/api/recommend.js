// 요청만 담당
// recommendByImage(file, limit, textQuery) 함수 하나
// FormData 만들고 fetch → JSON 반환

export async function recommendByImage(
  file,
  limit = 8,
  textQuery = '',
  category = '',
  gender = ''
) {
  const form = new FormData()

  // 1) 이미지 파일
  form.append('image', file)

  // 2) 숫자/문자도 FormData에 넣을 수 있음 (자동으로 문자열로 들어감)
  form.append('limit', String(limit))

  // 3) 텍스트도 같이 전송 (스프링에서 @RequestParam("textQuery")로 받기)
  //    빈 문자열이면 백엔드에서 무시하거나, q 튜닝에 쓰면 됨
  form.append('textQuery', textQuery)
  // + 카테고리, 성별도 추가로 보내기
  form.append('category', category) // 추가
  form.append('gender', gender) // 추가

  const res = await fetch('/api/v1/recommend/image', {
    method: 'POST',
    body: form,
  })

  let data = null
  let text = ''

  try {
    data = await res.json()
  } catch {
    text = await res.text().catch(() => '')
  }

  if (!res.ok) {
    console.error('[recommendByImage] HTTP', res.status, data ?? text)
    if (data?.error) return data
    throw new Error(`HTTP_${res.status}`)
  }

  return data
}
