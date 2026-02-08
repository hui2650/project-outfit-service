import { uid } from './uid.js'

/**
 * createTurn({ file, previewUrl, textQuery, category, gender })
 *
 * "turn" 이란?
 * - 사용자가 "추천받기" 버튼을 한 번 눌렀을 때 생성되는 하나의 요청 단위
 * - 채팅 UI에서 말풍선 묶음 1세트라고 보면 됨
 *
 * turn이 필요한 이유
 * 1) 요청 단위로 로딩/완료/에러 상태를 따로 관리할 수 있음
 * 2) 나중에 히스토리 탭 만들 때 "요청 기록"을 turn 단위로 저장/표시 가능
 * 3) 같은 turn 안에 messages를 쌓아 "대화 흐름"을 만들 수 있음
 *
 * 파라미터 설명
 * - file: 사용자가 업로드한 실제 File 객체(서버로 보낼 원본)
 * - previewUrl: 브라우저에서만 쓰는 blob url (화면 미리보기용)
 * - textQuery: 사용자가 입력한 텍스트(검색 보조)
 * - category/gender: 필수 선택값(추천 정확도 향상)
 *
 * 반환하는 turn 구조
 * - id: 프론트에서 만든 turn id (UI 관리용)
 * - requestId: 서버가 만든 requestId (서버/DB 식별용) -> 응답 오면 채워짐
 * - createdAt: 정렬/시간 표시용
 * - input: 이 turn을 만든 입력 스냅샷(히스토리/재추천에 필요)
 * - status: loading/done/error 상태
 * - error: 에러 정보(있을 때만)
 * - messages: 실제 UI가 렌더링할 말풍선 배열 (중요!)
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
     * turn 고유 id (클라이언트 생성)
     * - 예: "turn_1700000000000"
     * - server requestId와 역할이 다름 (이건 UI용)
     */
    id: 'turn_' + Date.now(),
    /**
     * requestId (서버 생성)
     * - 서버에서 요청을 식별하는 값
     * - 첫 요청 생성 시점에는 아직 없으므로 null
     * - 응답 받으면 Home/useRecommend에서 updateTurn으로 채움
     */
    requestId: null,
    /**
     * turn 생성 시간(프론트)
     * - 히스토리 정렬, 시간 표시 등에 사용 가능
     */
    createdAt: Date.now(),
    /**
     * input 스냅샷
     * - 이 turn을 만든 "원본 입력"을 저장해둠
     * - 나중에 "같은 이미지로 다시 추천" 같은 재요청을 할 때 필요
     * - 히스토리 탭에서 "사용자가 어떤 조건으로 추천받았는지" 재현 가능
     */
    input: {
      file, // 서버로 보낼 원본 File
      previewUrl, // 화면 미리보기 blob url
      textQuery,
      category,
      gender,
    },
    /**
     * status
     * - 'loading': 서버 응답 기다리는 중
     * - 'done': 정상 응답 받아서 결과 렌더 가능
     * - 'error': 요청 실패(네트워크/서버에러)
     */
    status: 'loading',
    /**
     * error 객체
     * - status가 error일 때만 채움
     * - 예: { code: 'NETWORK_ERROR', message: '서버 연결이 불안정해' }
     */
    error: null,
    /**
     * messages: 채팅 UI 렌더 기준 데이터
     * - turn을 만들자마자 유저 input 메시지를 바로 넣는다
     *   => "요청 보내는 즉시 화면에 유저 말풍선이 뜨게" 할 때 유용
     *
     * msg 구조 통일
     * - id: uid() (React key / 메시지 구분)
     * - role: 'user' | 'assistant'
     * - type: 'input' | 'text' | 'carousel' | 'error'
     *
     * 여기서는 "사용자가 보낸 입력"을 type='input'으로 넣는다.
     */
    messages: [
      {
        id: uid(),
        role: 'user',
        type: 'input',
        previewUrl, // UserInputPreview에서 이미지 미리보기로 사용
        text: textQuery, // UserInputPreview에서 텍스트 미리보기로 사용
      },
    ],
  }
}
