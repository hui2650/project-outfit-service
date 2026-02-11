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

    // 타임아웃(무한 로딩 방지)
    const TIMEOUT_MS = 25000

    // 타임아웃 Promise
    const timeoutPromise = new Promise((_, reject) => {
      const id = setTimeout(() => {
        clearTimeout(id)
        reject(new Error('TIMEOUT'))
      }, TIMEOUT_MS)
    })

    try {
      // 1) 서버 호출 (+ 타임아웃 레이스)
      const resp = await Promise.race([
        recommendByImage(file, 8, textQuery, category, gender),
        timeoutPromise,
      ])
      console.log(' resp received:', resp)

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

      const itemsWithKey = (resp?.items ?? []).map((it, idx) => ({
        ...it,
        itemKey:
          it.itemKey ??
          it.imageUrl ??
          `${turnId}_${requestId ?? 'noReq'}_${it.rank ?? idx}`,
      }))

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
      console.log(' requestRecommend error:', e)

      //  에러 분기(타임아웃 vs 일반 네트워크)
      const isTimeout =
        e?.message === 'TIMEOUT' ||
        String(e?.message || '')
          .toUpperCase()
          .includes('TIMEOUT')

      const err = isTimeout
        ? {
            code: 'TIMEOUT',
            message: `응답이 너무 오래 걸려서 중단했어. (약 ${Math.round(
              TIMEOUT_MS / 1000
            )}초) 서버가 켜져 있는지 확인하고 다시 시도해줘.`,
          }
        : {
            code: 'NETWORK_ERROR',
            message: '서버 연결이 불안정해. 다시 시도해줘.',
          }

      updateTurn(turnId, (t) => ({
        ...t,
        status: 'error',
        error: err,
        messages: [
          ...t.messages,
          { id: uid(), role: 'assistant', type: 'error', ...err },
        ],
      }))

      // 호출부에서 필요하면 잡을 수 있게 throw 유지
      throw e
    } finally {
      console.groupEnd()
    }
  }

  return { requestRecommend }
}
