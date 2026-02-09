import { recommendByImage } from '../api/recommend'
import { uid } from '../utils/uid'

/**
 * useRecommend({ updateTurn })
 *
 * 역할
 * - "추천 API 호출" + "응답을 turn(messages)에 반영"을 전담하는 훅
 * - Home.jsx에서 비즈니스 로직(서버 통신/turn 업데이트)을 걷어내서 코드 짧게 만듦
 *
 * 외부에서 주입받는 updateTurn의 의미
 * - updateTurn(turnId, updater)
 * - 특정 turn을 찾아서 안전하게(불변 업데이트로) 수정하는 함수
 * - 이 훅은 chatLogs 전체를 모르고, "turnId 기준으로 업데이트 요청"만 함
 *
 * ⚠️ 이 훅의 핵심 규칙
 * 1) 서버 응답 성공 => turn.status = 'done' + messages에 (AI text + carousel) 추가
 * 2) 서버가 JSON 에러(resp.error) => turn.status = 'error' + messages에 error 추가
 * 3) 네트워크 예외(fetch 실패) => turn.status = 'error' + messages에 NETWORK_ERROR 추가
 *
 * 서버 응답 포맷(프론트 규약)
 * - 성공: { requestId: string|null, items: [...] }
 * - 실패: { error: { code: string, message: string } }
 *
 * items는 캐러셀로 바로 렌더할 배열(8개)
 */
export const useRecommend = ({ updateTurn }) => {
  /**
   * requestRecommend({ turnId, file, textQuery, category, gender })
   *
   * 언제 호출?
   * - 사용자가 "추천받기" 누른 직후 (새 turn이 append 된 다음)
   *
   * 반드시 turnId를 받는 이유
   * - 요청을 보낸 turn이 여러 개일 수 있음(연속으로 추천 누르는 경우)
   * - 응답이 돌아왔을 때 "어느 turn에 꽂아야 하는지" 식별하려면 turnId가 필요
   *
   * file/textQuery/category/gender를 인자로 받는 이유
   * - 훅이 Home의 state를 직접 참조하면 의존성이 꼬임
   * - 호출 시점의 값을 "스냅샷"으로 넘겨야 요청이 안정적
   */
  const requestRecommend = async ({
    turnId,
    file,
    textQuery,
    category,
    gender,
  }) => {
    try {
      /**
       * 1) 서버 호출
       * - recommendByImage는 multipart form-data로 Spring에 전달
       * - Spring이 requestId 만들고, python 처리하고, 최종 JSON 반환
       */
      const resp = await recommendByImage(file, 8, textQuery, category, gender)

      /**
       * 2) 서버가 "정상 HTTP"지만 JSON에 error를 담아서 준 경우
       * - 예: validation 실패, python 에러, 내부 처리 실패 등
       * - 이 경우 turn을 error 상태로 바꾸고,
       *   UI에 에러 말풍선을 추가한다.
       */
      if (resp?.error) {
        updateTurn(turnId, (t) => ({
          ...t,
          status: 'error',
          error: resp.error,

          // turn.messages는 "렌더 기준"이므로
          // 에러도 messages에 쌓아주면 채팅 UI에서 바로 표시 가능
          messages: [
            ...t.messages,
            { id: uid(), role: 'assistant', type: 'error', ...resp.error },
          ],
        }))
        return
      }

      /**
       * 3) 성공 응답 처리
       * - requestId: 서버가 만든 요청 식별자(히스토리/로그/DB 연결용)
       * - items: 캐러셀에 뿌릴 추천 이미지/메타데이터 배열
       *
       * 여기서 turn을 done으로 바꾸고,
       * messages에 "AI 텍스트" + "캐러셀"을 순서대로 append 한다.
       *
       * ⚠️ 주의: resp.items가 없을 수도 있으니 항상 ?? []로 방어
       */
      updateTurn(turnId, (t) => ({
        ...t,
        status: 'done',
        requestId: resp.requestId ?? null,
        messages: [
          ...t.messages,

          // (선택) AI 텍스트 한 줄
          // - 너 UX 기준으로 "AI는 처음에만 말한다"면 유지 OK
          {
            id: uid(),
            role: 'assistant',
            type: 'text',
            content:
              '이 아이템이면 이런 느낌이 잘 어울려. 아래 후보 중 골라봐!',
          },
          // 캐러셀(결과)
          {
            id: uid(),
            role: 'assistant',
            type: 'carousel',
            requestId: resp.requestId ?? null,
            items: resp.items ?? [],
          },
        ],
      }))
    } catch {
      /**
       * 4) 네트워크 레벨 에러
       * - fetch 자체가 실패한 경우 (서버 다운, CORS, 연결 끊김 등)
       * - 서버가 JSON을 준 게 아니므로 resp.error 같은 것도 없음
       * - 우리가 통일된 에러 포맷으로 만들어서 UI에 넣는다
       */
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
    }
  }

  return { requestRecommend }
}
