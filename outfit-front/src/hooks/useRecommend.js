// src/hooks/useRecommend.js
import { recommendByImage } from '../api/recommend'
import { useAppData } from '../store/appDataStore'
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

const pickAssistantMessage = ({ category, gender, textQuery, itemsLen }) => {
  // 결과가 0개면 다른 문구
  if (itemsLen === 0) {
    return '조건에 맞는 후보를 찾지 못했어요. 카테고리나 키워드를 살짝 바꿔서 다시 시도해보시겠어요?'
  }

  const hasQuery = Boolean(textQuery && textQuery.trim().length > 0)

  const pool = []

  // 기본 템플릿
  pool.push(
    '이 아이템에 잘 어울리는 스타일을 정리해봤어요. 아래에서 골라보세요!'
  )
  pool.push(
    '분위기에 맞는 코디 후보를 모아봤어요. 마음에 드는 걸 선택해보세요.'
  )
  pool.push('분위기 흐름이 자연스러운 스타일들로 정리했어요. 확인해보세요!')
  pool.push('전체 밸런스가 잘 맞는 후보들로 골라봤어요.')
  pool.push(
    '이 아이템 기준으로 어울리는 스타일들을 가져왔어요. 아래에서 선택해보세요!'
  )
  pool.push('무드가 자연스럽게 이어지는 코디들로 정리했어요.')
  pool.push('데일리로 활용하기 좋은 스타일들 위주로 추려봤어요.')

  // 키워드가 있으면 ‘반영’ 느낌
  if (hasQuery) {
    pool.push(
      `"${textQuery.trim()}" 느낌에 맞춰 후보를 골라봤어요. 아래에서 확인해보세요!`
    )
    pool.push(
      '입력해주신 키워드를 반영해 스타일을 추려봤어요. 마음에 드는 코디를 선택해보세요!'
    )
  }

  // 카테고리별 톤(가벼운 맞춤)
  if (category === 'footwear') {
    pool.push(
      '신발을 중심으로 전체 밸런스가 좋은 코디를 골라봤어요. 아래에서 확인해보세요!'
    )
  }

  if (category === 'outerwear') {
    pool.push('아우터는 실루엣이 중요하죠. 핏이 예쁜 후보들로 정리했어요!')
  }

  // 랜덤 선택
  return pool[Math.floor(Math.random() * pool.length)]
}

export const useRecommend = ({ updateTurn, onHistoryTurn }) => {
  const { guest } = useAppData()

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
    const TIMEOUT_MS = 60000

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
        recommendByImage(
          file,
          8,
          textQuery,
          category,
          gender,
          guest?.guestId ?? null,
          guest?.nickname ?? '',
          guest?.style ?? ''
        ),
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
            content: pickAssistantMessage({
              category,
              gender,
              textQuery,
              itemsLen: itemsWithKey.length,
            }),
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
            message: `응답이 너무 오래 걸려서 중단되었습니다. (약 ${Math.round(
              TIMEOUT_MS / 1000
            )}초) 서버가 켜져 있는지 확인하고 다시 시도해주세요.`,
          }
        : {
            code: 'NETWORK_ERROR',
            message: '서버 연결이 불안정합니다. 다시 시도해주세요.',
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
