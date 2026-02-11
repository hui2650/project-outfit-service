// src/hooks/useRecommend.js
import { recommendByImage } from '../api/recommend'
import { uid } from '../utils/uid'

/**
 * useRecommend({ updateTurn, onHistoryTurn })
 *
 * - 서버 추천 호출 + turn(messages) 업데이트 담당 훅
 * - updateTurn(turnId, updater): turn 1개만 불변 업데이트
 * - onHistoryTurn?(historyTurn): 결과를 history store에 저장 (Home에서 주입)
 *
 * 서버 응답 규약:
 * - 성공: { requestId: string|null, items: [...] }
 * - 실패: { error: { code: string, message: string } }
 */
export const useRecommend = ({ updateTurn, onHistoryTurn }) => {
  const requestRecommend = async ({
    turnId,
    file,
    textQuery,
    category,
    gender,
  }) => {
    console.groupCollapsed(`🧠 [useRecommend] turnId=${turnId}`)
    console.log('▶️ start', {
      file: file ? { name: file.name, type: file.type, size: file.size } : null,
      textQuery,
      category,
      gender,
    })

    try {
      // 1) 서버 호출
      const resp = await recommendByImage(file, 8, textQuery, category, gender)
      console.log('✅ resp received:', resp)

      // 2) JSON 에러 포맷으로 온 경우
      if (resp?.error) {
        updateTurn(turnId, (t) => ({
          ...t,
          status: 'error',
          error: resp.error,
          messages: [
            ...t.messages,
            { id: uid(), role: 'assistant', type: 'error', ...resp.error },
          ],
        }))
        return
      }

      // 3) 성공
      const requestId = resp?.requestId ?? null

      // ✅ itemKey 붙이기 (좋아요/히스토리 핵심)
      // - 가능한 한 "변하지 않는 키" 우선
      // - imageUrl이 있으면 그걸 쓰고, 없으면 requestId+rank/idx 조합
      const itemsWithKey = (resp?.items ?? []).map((it, idx) => ({
        ...it,
        itemKey:
          it.itemKey ??
          it.imageUrl ??
          `${turnId}_${requestId ?? 'noReq'}_${it.rank ?? idx}`,
      }))

      // ✅ 히스토리 저장 (훅 호출 X, 콜백만)
      // - file은 localStorage에 못 넣으니 meta만 저장
      onHistoryTurn?.({
        turnId,
        requestId,
        createdAt: Date.now(),
        input: {
          textQuery,
          category,
          gender,
          fileMeta: file
            ? { name: file.name, type: file.type, size: file.size }
            : null,
        },
        items: itemsWithKey,
      })

      // ✅ turn 업데이트 (UI에는 itemsWithKey를 넣어야 LikeButton이 정상)
      updateTurn(turnId, (t) => ({
        ...t,
        status: 'done',
        requestId,
        messages: [
          ...t.messages,
          {
            id: uid(),
            role: 'assistant',
            type: 'text',
            content:
              '이 아이템이면 이런 느낌이 잘 어울려. 아래 후보 중 골라봐!',
          },
          {
            id: uid(),
            role: 'assistant',
            type: 'carousel',
            requestId,
            items: itemsWithKey,
          },
        ],
      }))
    } catch (e) {
      // 4) 네트워크/런타임 예외
      console.log('❌ requestRecommend error:', e)

      console.log('SPRING RESPONSE:', resp)

      const err = { code: 'NETWORK_ERROR', message: '서버 연결이 불안정해' }
      updateTurn(turnId, (t) => ({
        ...t,
        status: 'error',
        error: err,
        messages: [
          ...t.messages,
          { id: uid(), role: 'assistant', type: 'error', ...err },
        ],
      }))
    } finally {
      console.groupEnd()
    }
  }

  return { requestRecommend }
}
