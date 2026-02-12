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

  // 3) 텍스트도 같이 전송
  form.append('textQuery', textQuery)

  // + 카테고리, 성별도 추가로 보내기
  form.append('category', category)
  form.append('gender', gender)

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
