from __future__ import annotations

import os
from typing import Dict, List, Optional

import httpx

# =========================
# LLM CHAT (OpenAI Responses API)
# =========================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

# ---------
# guard: 패션/코디/앱 맥락 외 질문 차단
# ---------
FASHION_KEYWORDS = [
    "코디", "패션", "옷", "착장", "룩", "스타일", "스타일링", "핏", "무드",
    "상의", "하의", "아우터", "자켓", "코트", "신발", "운동화", "가방",
    "색", "컬러", "블랙", "화이트", "베이지", "브라운", "네이비",
    "데일리룩", "스트릿", "미니멀", "캐주얼", "포멀", "오피스룩", "데이트룩",
    "코디추천", "룩북", "스냅", "ootd",
    "추천", "후보", "1번", "2번", "3번", "첫번째", "두번째", "세번째",
    "이거 어울려", "매치", "조합", "어떻게 입", "뭐 입", "설명해줘",
]

def is_fashion_query(text: str) -> bool:
    t = (text or "").strip().lower()
    if not t:
        return False
    # 숫자만 보내는 경우(예: "1", "1번")는 코디 설명으로 간주
    if t in {"1", "2", "3", "4", "5", "6", "7", "8"}:
        return True
    for kw in FASHION_KEYWORDS:
        if kw.lower() in t:
            return True
    return False


# ---------
# OpenAI call (Responses API)
# ---------
async def call_openai_responses(messages: List[Dict[str, str]], system: Optional[str] = None) -> str:
    if not OPENAI_API_KEY:
        raise RuntimeError("Missing OPENAI_API_KEY")

    input_items: List[Dict[str, str]] = []
    if system:
        input_items.append({"role": "system", "content": system})
    input_items.extend(messages)

    payload = {"model": OPENAI_MODEL, "input": input_items}
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(f"{OPENAI_BASE_URL}/responses", headers=headers, json=payload)
        r.raise_for_status()
        data = r.json()

    reply = data.get("output_text")
    if isinstance(reply, str) and reply.strip():
        return reply.strip()

    out = data.get("output", [])
    texts: List[str] = []
    if isinstance(out, list):
        for item in out:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "message":
                content = item.get("content", [])
                if isinstance(content, list):
                    for part in content:
                        if isinstance(part, dict) and part.get("type") == "output_text":
                            t = part.get("text", "")
                            if t:
                                texts.append(t)
    return "\n".join(texts).strip()
