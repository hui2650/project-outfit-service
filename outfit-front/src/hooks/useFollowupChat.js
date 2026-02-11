// src/hooks/useFollowupChat.js
import { askFollowup } from '../api/chat'
import { uid } from '../utils/uid'

export const useFollowupChat = ({ updateTurn }) => {
  const sendChat = async ({
    turnId,
    text,
    requestId = null,
    items = [],
    category = '',
    gender = '',
  }) => {
    const userMsgId = uid()
    const assistantMsgId = uid()

    // 1) UI에 먼저 user 메시지 + assistant placeholder 추가
    updateTurn(turnId, (t) => ({
      ...t,
      messages: [
        ...t.messages,
        { id: userMsgId, role: 'user', type: 'text', content: text },
        { id: assistantMsgId, role: 'assistant', type: 'text', content: '…' }, // 로딩 표시
      ],
    }))

    try {
      const resp = await askFollowup({
        text,
        requestId,
        items,
        category,
        gender,
      })

      if (resp?.error) {
        // placeholder를 에러로 치환
        updateTurn(turnId, (t) => ({
          ...t,
          messages: t.messages.map((m) =>
            m.id === assistantMsgId
              ? {
                  id: m.id,
                  role: 'assistant',
                  type: 'error',
                  message: resp.error.message,
                  code: resp.error.code,
                }
              : m
          ),
        }))
        return
      }

      const answer = resp?.answer ?? '답변을 생성하지 못했어.'

      // 2) placeholder를 진짜 답변으로 치환
      updateTurn(turnId, (t) => ({
        ...t,
        messages: t.messages.map((m) =>
          m.id === assistantMsgId ? { ...m, type: 'text', content: answer } : m
        ),
      }))
    } catch (e) {
      updateTurn(turnId, (t) => ({
        ...t,
        messages: t.messages.map((m) =>
          m.id === assistantMsgId
            ? {
                id: m.id,
                role: 'assistant',
                type: 'error',
                message: '서버 연결이 불안정해',
                code: 'NETWORK_ERROR',
              }
            : m
        ),
      }))
    }
  }

  return { sendChat }
}
