import { uid } from './uid.js'

/**
 * createTurn()
 *
 * turn = "추천 요청 1회" 단위
 * - 사용자가 이미지/옵션 선택 후 "추천받기"를 눌렀을 때 만들어지는 한 덩어리 상태
 *
 * 왜 turn이 중요한가
 * - 채팅 UI는 메시지가 계속 쌓이지만, 추천 결과는 요청 단위로 묶여야 UX가 깔끔함
 * - 로딩/완료/에러는 메시지가 아니라 "요청 단위"로 관리하는 게 맞다
 * - 히스토리도 "요청 단위 기록"이 가장 자연스럽다
 *
 * input 스냅샷을 저장하는 이유
 * - 요청 당시의 file/previewUrl/textQuery/category/gender를 그대로 재현 가능
 * - "같은 조건으로 다시 추천" 기능을 만들 때 추가 입력 없이 재요청 가능
 */
export const createTurn = ({
  file,
  previewUrl,
  textQuery,
  category,
  gender,
}) => {
  return {
    /**
     * id: 프론트에서 만든 turn 식별자
     *
     * 특징
     * - UI에서 Turn 컴포넌트 key로 쓰고
     * - updateTurnById / updateTurn 같은 함수로 "턴 하나"를 찾아 업데이트하는 기준이 됨
     *
     * 주의
     * - Date.now()는 같은 ms에 두 개가 생성될 가능성이 아주 낮지만 존재
     * - 완벽히 안전하려면 uid()로 바꾸는 것도 방법
     */
    id: 'turn_' + Date.now(),

    /**
     * requestId: 서버가 부여하는 요청 식별자
     * - 처음에는 없으므로 null
     * - 서버 응답이 오면 turn 업데이트로 채워 넣는다
     * - followup chat에서 대화 문맥을 requestId로 이어가면 서버 측 추적이 쉬워짐
     */
    requestId: null,

    /**
     * createdAt: turn 생성 시간
     * - 히스토리/정렬/표시에서 사용
     */
    createdAt: Date.now(),

    /**
     * input: 이 turn의 입력 스냅샷
     * - file: 서버 업로드용 원본 (FormData로 보낼 대상)
     * - previewUrl: 화면 표시용 blob url (브라우저 전용)
     * - textQuery/category/gender: 추천 조건
     */
    input: {
      file,
      previewUrl,
      textQuery,
      category,
      gender,
    },

    /**
     * status: turn 레벨 상태
     * - loading: 추천 생성 중 (로딩 Turn 렌더링)
     * - done: 결과를 messages로 렌더 가능
     * - error: error 객체와 함께 오류 UI 표시 가능
     */
    status: 'loading',

    /**
     * error: 에러 정보(있으면)
     * - 네트워크 실패나 서버에서 내려주는 코드 등을 저장
     * - turn 단위로 "어떤 요청이 실패했는지" 보여줄 수 있음
     */
    error: null,

    /**
     * messages: UI 렌더링 기준 데이터
     *
     * 설계 포인트
     * - turn 생성 직후에도 사용자 입력 미리보기(input 메시지)를 넣어
     *   화면에 "내가 보낸 요청"이 바로 반영되게 만든다
     *
     * type: 'input'
     * - ChatPreview에서 이미지+텍스트를 렌더하는 용도
     */
    messages: [
      {
        id: uid(),
        role: 'user',
        type: 'input',
        previewUrl,
        text: textQuery,
      },
    ],
  }
}
