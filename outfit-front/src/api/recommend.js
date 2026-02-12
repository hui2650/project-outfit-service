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

  form.append('image', file)
  form.append('limit', String(limit))
  form.append('textQuery', textQuery)
  form.append('category', category)
  form.append('gender', gender)

  // ✅ FastAPI가 Form으로 받는 필드들
  form.append('guestId', guestId ?? '')
  form.append('nickname', nickname ?? '')
  form.append('style', style ?? '')

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
