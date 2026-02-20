/**
 * isPlaceholderText(s)
 *
 * 목적
 * - UI에서 assistant placeholder로 쓰는 텍스트(…/loading/빈 값)를
 *   문맥(prevAnswer) 추출할 때 제외하기 위한 필터
 */
function isPlaceholderText(s) {
  const t = (s ?? '').trim()
  return !t || t === '…' || t === '...' || t.toLowerCase() === 'loading'
}

/**
 * getLastAssistantText(chatLogs)
 *
 * 목적
 * - 현재 대화 로그에서 "마지막 유효한 assistant 답변"을 찾는다
 * - followup 요청에 prevAnswer로 포함시키기 위함
 *
 * 왜 prevAnswer가 필요한가
 * - 서버가 이전 답변을 참고하면 followup 답변 품질이 좋아짐
 * - 다만 전체 로그를 모두 보내면 payload가 커지므로,
 *   마지막 답변만 요약해서 보내는 방식이 실용적
 *
 * 로그 구조가 여러 형태일 수 있어 케이스별로 방어
 * - role/content 기반
 * - type/sender 기반
 * - answer 기반
 */
function getLastAssistantText(chatLogs = []) {
  for (let i = chatLogs.length - 1; i >= 0; i--) {
    const m = chatLogs[i]
    if (!m) continue

    // 케이스1: role/content 기반 (현재 너의 AIMessage 구조와 잘 맞는 형태)
    if (m.role === 'assistant' && typeof m.content === 'string') {
      const c = m.content.trim()
      if (c && !isPlaceholderText(c)) return c
    }

    // 케이스2: type/sender 기반 (이전/다른 구조 호환)
    if (
      (m.type === 'bot' || m.sender === 'assistant') &&
      typeof m.text === 'string'
    ) {
      const t = m.text.trim()
      if (t && !isPlaceholderText(t)) return t
    }

    // 케이스3: answer 필드 기반 (응답 포맷이 다른 경우 대비)
    if (m.role === 'assistant' && typeof m.answer === 'string') {
      const a = m.answer.trim()
      if (a && !isPlaceholderText(a)) return a
    }
  }
  return ''
}

/**
 * askFollowup()
 *
 * 목적
 * - followup 채팅 요청을 서버로 전송
 * - 이전 답변(prevAnswer)을 함께 보내 문맥 유지
 *
 * payload 구성
 * - text: 유저 질문
 * - requestId: 첫 추천 요청의 requestId(있으면 대화 연결에 도움)
 * - items/category/gender: 추천 결과/조건 컨텍스트
 * - guestId/nickname/style: 게스트 사용자 상태
 * - prevAnswer: 마지막 assistant 답변 일부(800자 제한)
 */
export async function askFollowup({
  text,
  requestId = null,
  items = [],
  category = '',
  gender = '',
  guestId = null,
  nickname = '',
  style = '',
  chatLogs = [],
}) {
  // 마지막 assistant 답변 추출
  const prevAnswerRaw = getLastAssistantText(chatLogs)

  // payload 과도 확장을 막기 위해 길이 제한
  const prevAnswer = prevAnswerRaw.slice(0, 800)

  const payload = {
    text,
    requestId,
    items,
    category,
    gender,
    guestId,
    nickname,
    style,
    prevAnswer,
  }

  // 디버깅: 실제 서버에 전달되는 payload 확인
  console.log('[chat] payload:', payload)

  const res = await fetch('/api/v1/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

  /**
   * 응답 파싱 전략
   * - res.json() 대신 res.text()로 먼저 받은 후 JSON.parse
   *
   * 이유
   * - 서버가 에러 상황에서 JSON이 아닌 문자열/HTML을 보낼 수 있음
   * - 이 경우에도 rawBody를 확보해 디버깅이 쉬워짐
   */
  const rawBody = await res.text()

  let data
  try {
    data = rawBody ? JSON.parse(rawBody) : {}
  } catch {
    // JSON 파싱 실패 시에도 error 형태로 래핑해 UI 처리 경로를 통일
    data = { error: { message: rawBody || 'Invalid JSON', code: 'BAD_JSON' } }
  }

  console.log('[chat] status:', res.status)
  console.log('[chat] data:', data)
  console.log('[chat] rawBody:', rawBody)

  /**
   * HTTP 실패 처리
   * - 서버가 { error }를 주면 그걸 반환해서 UI에 표시
   * - 아니면 throw로 상위에서 공통 에러 처리
   */
  if (!res.ok) {
    if (data?.error) return data
    throw new Error('HTTP_ERROR')
  }

  // 성공 시: { answer, requestId } 형태 기대
  return data
}
