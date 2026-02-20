// src/hooks/useFollowupChat.js
import { askFollowup } from '../api/chat'
import { uid } from '../utils/uid'
import { useAppData } from '../store/appDataStore.jsx'

/**
 * useFollowupChat({ updateTurn })
 *
 * 목적
 * - 기존 turn 내부의 messages 배열에
 *   user 메시지 + assistant 메시지를 추가하고
 * - 서버 응답을 받아 placeholder를 실제 답변으로 교체
 *
 * 핵심 구조
 * - optimistic UI 적용
 * - assistant 메시지를 먼저 placeholder("…")로 넣고
 * - 응답 오면 해당 id를 찾아 치환
 */
export const useFollowupChat = ({ updateTurn }) => {
  const { guest } = useAppData()

  const sendChat = async ({
    turnId,
    text,
    requestId = null,
    items = [],
    category = '',
    gender = '',
    messages = [],
  }) => {
    const userMsgId = uid()
    const assistantMsgId = uid()

    /**
     * 1단계: UI 선반영
     *
     * - user 메시지 추가
     * - assistant placeholder 추가
     *
     * 서버 응답 기다리지 않음
     */
    updateTurn(turnId, (t) => ({
      ...t,
      messages: [
        ...(t.messages ?? []),
        { id: userMsgId, role: 'user', type: 'text', content: text },
        { id: assistantMsgId, role: 'assistant', type: 'text', content: '…' },
      ],
    }))

    try {
      /**
       * 2단계: 서버 요청
       * guest 정보 포함해서 전달
       */
      const resp = await askFollowup({
        text,
        requestId,
        items,
        category,
        gender,
        chatLogs: messages,
        guestId: guest?.guestId ?? null,
        nickname: guest?.nickname ?? '',
        style: guest?.style ?? '',
      })

      /**
       * 서버가 error 형식으로 응답한 경우
       * placeholder를 error 타입 메시지로 교체
       */
      if (resp?.error) {
        updateTurn(turnId, (t) => ({
          ...t,
          messages: (t.messages ?? []).map((m) =>
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

      const answer = resp?.answer ?? '답변을 생성하지 못했습니다.'

      /**
       * 3단계: placeholder → 실제 답변으로 치환
       */
      updateTurn(turnId, (t) => ({
        ...t,
        messages: (t.messages ?? []).map((m) =>
          m.id === assistantMsgId ? { ...m, type: 'text', content: answer } : m
        ),
      }))
    } catch (e) {
      /**
       * 네트워크 오류 처리
       */
      updateTurn(turnId, (t) => ({
        ...t,
        messages: (t.messages ?? []).map((m) =>
          m.id === assistantMsgId
            ? {
                id: m.id,
                role: 'assistant',
                type: 'error',
                message: '서버 연결이 불안정합니다.',
                code: 'NETWORK_ERROR',
              }
            : m
        ),
      }))
    }
  }

  return { sendChat }
}
