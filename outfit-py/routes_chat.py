from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from main_llm import call_openai_responses, is_fashion_query

router = APIRouter()

# ---------
# Followup schema (front 유지)
# ---------
class FollowupReq(BaseModel):
    text: str
    requestId: Optional[str] = None
    items: List[Dict[str, Any]] = Field(default_factory=list)
    category: Optional[str] = ""
    gender: Optional[str] = ""

class FollowupResp(BaseModel):
    answer: str
    requestId: Optional[str] = None

# 기존 /chat 용
class ChatReq(BaseModel):
    messages: List[Dict[str, str]]
    system: Optional[str] = None

class ChatResp(BaseModel):
    reply: str


# ---------
# /api/v1/chat : 추천 결과(items) 기반 "코디 설명" 전용
# ---------
@router.post("/api/v1/chat", response_model=FollowupResp)
async def chat_followup(req: FollowupReq):
    # 1) 패션/코디 외 질문 차단
    if not is_fashion_query(req.text):
        return FollowupResp(
            answer="나는 이 앱에서는 패션/코디(추천 결과 설명, 스타일 조합, 착장 해석) 관련 질문만 도와줄 수 있어. 코디/스타일 질문으로 다시 말해줘!",
            requestId=req.requestId,
        )

    # 2) items 컨텍스트 만들기 (다운로드/이미지 열람 없이 메타만)
    items = req.items or []
    lines = []
    for i, it in enumerate(items[:8], start=1):
        title = (it.get("title") or "").strip()
        source = (it.get("source") or it.get("_source") or "").strip()
        tier = (it.get("tier") or "").strip()
        score = it.get("rankScore")
        url = (it.get("imageUrl") or "").strip()
        lines.append(f"{i}) title={title} | source={source} | tier={tier} | score={score} | url={url}")

    items_ctx = "\n".join(lines) if lines else "(no items)"

    # 3) system: 역할/제약/출력 규칙
    system = f"""
너는 패션 코디 추천 앱의 '후속 설명' 어시스턴트야.

제약:
- 이미지를 직접 보지 못한다. (다운로드/열람/스크린샷 상상 금지)
- 대신 사용자가 방금 본 추천 결과의 메타데이터(items)를 제공받는다.
- 메타(제목/소스/티어/점수) 기반으로 합리적으로 추정해서 설명한다.
- 과장하거나 "사진에서 보이는" 같은 표현은 금지. 반드시 "메타 기준으로 보면" 톤을 써라.

사용자 요청 처리:
- 사용자가 "첫번째/1번" 등 번호를 말하면 해당 번호 후보를 중심으로 설명.
- 번호가 없으면 1번을 기본으로 설명.
- 답변 형식(짧게 4~8문장):
  1) 한 줄로 무드 요약
  2) 상의/하의/신발/아우터 중 핵심 포인트 2~3개
  3) 어울리는 상황(데이트/출근/데일리 등) 1~2개
  4) 사용자가 다음에 바꾸면 좋은 옵션(색/핏/아이템) 1개 제안

추가 힌트:
- category={req.category}
- gender={req.gender}

추천 후보(items):
{items_ctx}
""".strip()

    msgs = [{"role": "user", "content": req.text}]
    reply = await call_openai_responses(msgs, system=system)
    return FollowupResp(answer=reply, requestId=req.requestId)


# ---------
# 기존 범용 /chat 유지
# ---------
@router.post("/chat", response_model=ChatResp)
async def chat(req: ChatReq):
    reply = await call_openai_responses(req.messages, req.system)
    return ChatResp(reply=reply)
