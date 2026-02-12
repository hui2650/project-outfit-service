# LLM 파트 ‘통째로’ 이 파일로 이동)

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

from .guards import is_fashion_query, is_greeting, is_help_query
from .llm_client import call_openai_responses
from .nickname_policy import decide_use_nickname
from prompts.followup_prompt import build_followup_system

# ---------
# Followup schema (front 유지)
# ---------
class FollowupReq(BaseModel):
    text: str
    requestId: Optional[str] = None
    items: List[Dict[str, Any]] = Field(default_factory=list)
    category: Optional[str] = ""
    gender: Optional[str] = ""
    guestId: Optional[str] = ""
    nickname: Optional[str] = ""
    style: Optional[str] = ""
    prevAnswer: Optional[str] = ""  # 이전 답변
    

class FollowupResp(BaseModel):
    answer: str
    requestId: Optional[str] = None

# 기존 /chat 용
class ChatReq(BaseModel):
    messages: List[Dict[str, str]]
    system: Optional[str] = None

class ChatResp(BaseModel):
    reply: str


def build_items_ctx(items: List[Dict[str, Any]], limit: int = 8) -> str:
    lines = []
    for i, it in enumerate((items or [])[:limit], start=1):
        title = (it.get("title") or "").strip()
        source = (it.get("source") or it.get("_source") or "").strip()
        tier = (it.get("tier") or "").strip()
        score = it.get("rankScore")
        url = (it.get("imageUrl") or "").strip()
        lines.append(f"{i}) title={title} | source={source} | tier={tier} | score={score} | url={url}")
    return "\n".join(lines) if lines else "(no items)"


def apply_greeting_prefix(answer: str, nickname: str, use_nickname: bool) -> str:
    a = (answer or "").lstrip()
    if a.startswith("안녕하세요"):
        return a  # 중복 방지

    nick = (nickname or "").strip()
    if use_nickname and nick:
        return f"안녕하세요 {nick}님, {a}"
    return f"안녕하세요, {a}"


async def handle_followup_chat(req: FollowupReq) -> FollowupResp:
    """
    req: FollowupReq (main.py에서 정의한 pydantic 모델 그대로 받기)
    return: {"answer": str, "requestId": Optional[str]}
    """
    t = (req.text or "").strip()

    allow = is_fashion_query(t) or is_greeting(t) or is_help_query(t)
    if not allow:
        return FollowupResp(
            answer="이 대화는 코디/스타일 설명과 앱 사용 안내만 도와줄 수 있어. 코디 번호(1~8)나 원하는 스타일로 물어봐줘!",
            requestId=req.requestId,
        )   

    category = (req.category or "").strip()
    gender = (req.gender or "").strip()

    items_ctx = build_items_ctx(req.items or [])

    use_nickname = decide_use_nickname(req.nickname, t, followup_prob=0.40)

    system = build_followup_system(
        nickname=req.nickname,
        style=req.style,
        category=category,
        gender=gender,
        use_nickname=use_nickname,
        items_ctx=items_ctx,
    )

    msgs: List[Dict[str, str]] = []
    if (req.prevAnswer or "").strip():
        msgs.append({"role": "assistant", "content": req.prevAnswer.strip()})
    msgs.append({"role": "user", "content": t})

    reply = await call_openai_responses(msgs, system=system)
    reply = str(reply or "")

    # 니 요구사항: "무조건 안녕하세요 ㅇㅇ님" 시작
    reply = apply_greeting_prefix(reply, req.nickname, use_nickname)

    return FollowupResp(
        answer=reply,
        requestId=req.requestId,
    )
