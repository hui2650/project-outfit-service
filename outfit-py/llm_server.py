# llm_server.py
from __future__ import annotations

import os
import re
import json
import time
import base64
import hashlib
from typing import Any, Dict, List, Optional, Tuple
 
import httpx
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


# =========================
# 0) UTF-8 JSON Response (핵심: 한글 깨짐 방지)
# =========================
class UTF8JSONResponse(JSONResponse):
    media_type = "application/json; charset=utf-8"


# =========================
# 1) Simple TTL Cache (MVP)
# =========================
class TTLCache:
    def __init__(self, ttl_seconds: int = 3600, max_items: int = 2000):
        self.ttl = ttl_seconds
        self.max_items = max_items
        self._store: Dict[str, Tuple[float, Any]] = {}

    def get(self, key: str) -> Optional[Any]:
        v = self._store.get(key)
        if not v:
            return None
        exp, val = v
        if time.time() > exp:
            self._store.pop(key, None)
            return None
        return val

    def set(self, key: str, val: Any):
        if len(self._store) >= self.max_items:
            # naive eviction
            k = next(iter(self._store.keys()))
            self._store.pop(k, None)
        self._store[key] = (time.time() + self.ttl, val)


# =========================
# 2) Env / Config
# =========================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()

MAX_IMAGE_BYTES = int(os.getenv("LLM_MAX_IMAGE_BYTES", "5242880"))  # 5MB
OPENAI_TIMEOUT = float(os.getenv("OPENAI_TIMEOUT", "60"))
DL_TIMEOUT = float(os.getenv("IMAGE_DL_TIMEOUT", "25"))

CACHE_EXTRACT = TTLCache(ttl_seconds=3600, max_items=1000)
CACHE_DESCRIBE = TTLCache(ttl_seconds=3600, max_items=1500)
CACHE_QA = TTLCache(ttl_seconds=1800, max_items=1500)


# =========================
# 3) Schemas (API)
# =========================
class DescribeRequest(BaseModel):
    imageUrl: str
    lang: str = "ko"
    detail: str = "short"  # short|medium (MVP)


class DescribeResponse(BaseModel):
    one_line: str
    style_points: List[str] = Field(..., min_length=3, max_length=3)
    tips: List[str] = Field(default_factory=list)
    outfit_json: Dict[str, Any] = Field(default_factory=dict)


class QARequest(BaseModel):
    outfit_json: Dict[str, Any]
    question: str


class QAResponse(BaseModel):
    answer: str
    confidence: float = 0.0
    grounded_on: List[str] = Field(default_factory=list)


# =========================
# 4) Prompt Templates (룩북 톤 + 규칙 강제)
# =========================
# outfit_json 스키마: 너무 복잡하면 모델이 흔들리므로 MVP로 고정
OUTFIT_JSON_SCHEMA = {
    "item": "string (주요 아이템 1개)",
    "palette": ["string (색감 키워드 1~4)"],
    "style_tags": ["string (스타일 태그 1~5)"],
    "occasion": ["string (상황/용도 1~4)"],
    "mood": ["string (무드 키워드 1~4)"],
    "notes": ["string (보조 메모 0~4)"],
    "confidence": "number (0~1, 정보 확실도)",
}

EXTRACT_SYSTEM = """\
너는 ‘룩북 코디 정보 추출기’다.
입력은 이미지(패션/코디 사진)다. 출력은 반드시 JSON만.
추측 금지: 브랜드/가격/소재 확정/성별/나이/직업 등은 이미지로 확실하지 않으면 쓰지 마라.
민감정보 금지: 얼굴/신원/외모평가(예쁘다/못생겼다 등) 관련 내용 금지.
불확실하면 "unknown"을 사용하고 confidence를 낮춰라.
"""

EXTRACT_USER = """\
아래 이미지에서 “룩북 카드”에 필요한 최소 코디 정보를 추출해줘.

[출력 JSON 스키마]
{schema}

규칙:
- item: 가장 중심이 되는 아이템 1개(예: 연청 데님, 베이지 트렌치 등). 확신 없으면 "unknown".
- palette/style_tags/occasion/mood/notes: 모르면 "unknown" 하나만 넣어도 됨.
- confidence: 0~1. 확신 없으면 0.2 이하.
"""

DESCRIBE_SYSTEM = """\
너는 “룩북 코디 에디터”다.
출력은 반드시 JSON만 한다. JSON 밖 텍스트 금지.
항상 한국어로 작성한다.
규칙(최우선):
- one_line: 20~32자(공백 포함) 1문장 카피
- style_points: 정확히 3개, 각 항목 18~40자, 바로 이해되게 “야무지게”
- tips: 2개까지, 행동형(예: ‘화이트 티 레이어드로 정리’)
추측 금지(브랜드/가격/소재 확정 등).
민감정보 금지(얼굴/나이/신원/외모평가).
"""

DESCRIBE_USER = """\
다음 “코디 요약 JSON”을 기반으로 룩북 카드용 문구를 만들어줘.

[코디 요약 JSON]
{outfit_json}

[출력 JSON 스키마]
{{
  "one_line": "20~32자 한 줄 카피",
  "style_points": ["포인트1", "포인트2", "포인트3"],
  "tips": ["실행 팁 1", "실행 팁 2"]
}}

추가 규칙:
- 과장 금지. “깔끔/담백/감성” 톤.
- one_line은 감성적이되 정보성 유지.
- style_points는 ‘왜 좋은지’가 바로 보이게.
"""

QA_SYSTEM = """\
너는 코디 Q&A 봇이다.
아래의 “코디 요약 JSON”만 근거로 답변해라.
정보가 부족하면 “추정 불가”라고 답해라.
항상 한국어로, 2~4문장 이내로 짧게 답해라.
출력은 반드시 JSON만 한다. JSON 밖 텍스트 금지.
민감정보(얼굴/나이/신원/외모평가) 관련 질문은 정중히 거절한다.
"""

QA_USER = """\
[코디 요약 JSON]
{outfit_json}

[사용자 질문]
{question}

[출력 JSON 스키마]
{{
  "answer": "답변(2~4문장)",
  "confidence": 0.0,
  "grounded_on": ["근거로 쓴 필드명들"]
}}
"""

# -------------------------
# OpenAI response_format: json_schema (원천 봉쇄)
# -------------------------
DESCRIBE_JSON_SCHEMA = {
    "name": "describe_card_copy",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "one_line": {"type": "string"},
            "style_points": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 3,
                "maxItems": 3,
            },
            "tips": {"type": "array", "items": {"type": "string"}, "minItems": 0, "maxItems": 2},
        },
        "required": ["one_line", "style_points", "tips"],
    },
}

QA_JSON_SCHEMA = {
    "name": "outfit_qa",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "answer": {"type": "string"},
            "confidence": {"type": "number"},
            "grounded_on": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 0,
                "maxItems": 8,
            },
        },
        "required": ["answer", "confidence", "grounded_on"],
    },
}

EXTRACT_JSON_SCHEMA = {
    "name": "extract_outfit",
    "schema": {
        "type": "object",
        # MVP: 필드 추가가 나와도 받아주되 normalize_outfit이 최종 정리
        "additionalProperties": True,
        "properties": {
            "item": {"type": "string"},
            "palette": {"type": "array", "items": {"type": "string"}},
            "style_tags": {"type": "array", "items": {"type": "string"}},
            "occasion": {"type": "array", "items": {"type": "string"}},
            "mood": {"type": "array", "items": {"type": "string"}},
            "notes": {"type": "array", "items": {"type": "string"}},
            "confidence": {"type": "number"},
        },
        "required": ["item", "palette", "style_tags", "occasion", "mood", "notes", "confidence"],
    },
}


# =========================
# 5) Utils
# =========================
def _sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()


def _is_ascii(s: str) -> bool:
    try:
        s.encode("ascii")
        return True
    except Exception:
        return False


def _ensure_openai_key():
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY missing")
    # UnicodeEncodeError 방지: key에 비ASCII가 섞이면 즉시 차단
    if not _is_ascii(OPENAI_API_KEY):
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY contains non-ascii characters (키 재발급/복붙 확인)",
        )


# --- 복구형 JSON normalize (패치 반영) ---
_CODE_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)


def _strip_code_fences(s: str) -> str:
    m = _CODE_FENCE_RE.search(s)
    return (m.group(1) if m else s).strip()


def _light_json_repair(s: str) -> str:
    # 안전한 범위의 복구만(과도한 수선 금지)
    s = s.replace("“", '"').replace("”", '"').replace("’", "'").replace("‘", "'")
    # trailing comma 제거: { "a": 1, } / [1,2,]
    s = re.sub(r",\s*([}\]])", r"\1", s)
    return s


def _extract_json_candidates(s: str) -> List[str]:
    """
    문자열 내부에서 균형 잡힌 JSON 객체/배열 후보를 스택으로 추출.
    - '{...}' 또는 '[...]' 형태를 최대한 찾아냄
    - 문자열 리터럴 내부 brace는 무시
    """
    candidates: List[str] = []
    opens = {"{": "}", "[": "]"}
    closes = set(opens.values())

    for start, ch in enumerate(s):
        if ch not in opens:
            continue

        stack = [opens[ch]]
        i = start + 1
        in_str = False
        esc = False

        while i < len(s):
            c = s[i]
            if in_str:
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == '"':
                    in_str = False
            else:
                if c == '"':
                    in_str = True
                elif c in opens:
                    stack.append(opens[c])
                elif c in closes:
                    if not stack or c != stack[-1]:
                        break
                    stack.pop()
                    if not stack:
                        candidates.append(s[start : i + 1].strip())
                        break
            i += 1

    candidates.sort(key=len, reverse=True)
    uniq: List[str] = []
    seen = set()
    for c in candidates:
        if c not in seen:
            uniq.append(c)
            seen.add(c)
    return uniq


def _normalize_json_obj(x: Any) -> Dict[str, Any]:
    """
    OpenAI content가:
    - dict면 그대로
    - list면 {"items": ...}
    - str이면: 코드펜스 제거 -> (1) 전체 파싱 시도 -> (2) 내부 JSON 후보 추출 후 파싱
    실패하면 {"raw": "..."}로 격리
    """
    if isinstance(x, dict):
        return x
    if isinstance(x, list):
        return {"items": x}
    if x is None:
        return {"raw": ""}

    s0 = _strip_code_fences(str(x))

    for attempt in (s0, _light_json_repair(s0)):
        try:
            obj = json.loads(attempt)
            return obj if isinstance(obj, dict) else {"items": obj}
        except Exception:
            pass

    for cand in _extract_json_candidates(s0):
        for attempt in (cand, _light_json_repair(cand)):
            try:
                obj = json.loads(attempt)
                return obj if isinstance(obj, dict) else {"items": obj}
            except Exception:
                continue

    return {"raw": s0}


# --- /복구형 JSON normalize ---


def _coerce_describe_shape(obj: Dict[str, Any]) -> Dict[str, Any]:
    # style_points 3개 보장 + 문자열 정리 + 길이 컷
    one_line = str(obj.get("one_line", "")).strip()
    sps = obj.get("style_points", [])
    tips = obj.get("tips", [])

    if not isinstance(sps, list):
        sps = []
    if not isinstance(tips, list):
        tips = []

    sps = [str(x).strip() for x in sps if str(x).strip()]
    tips = [str(x).strip() for x in tips if str(x).strip()]

    while len(sps) < 3:
        sps.append("포인트를 정리해 깔끔하게 완성")
    sps = sps[:3]
    tips = tips[:2]

    def cut(s: str, n: int) -> str:
        s = re.sub(r"\s+", " ", s).strip()
        return s if len(s) <= n else s[:n].rstrip()

    one_line = cut(one_line, 36)  # 약간 여유

    # ✅ one_line이 비면 기본 카피 강제(깨진 JSON/RAW 대비)
    if not one_line:
        one_line = "담백하게 정리한 데일리 코디"

    sps = [cut(x, 48) for x in sps]
    tips = [cut(x, 48) for x in tips]

    obj["one_line"] = one_line
    obj["style_points"] = sps
    obj["tips"] = tips
    return obj


def _safe_content_type(ct: str) -> bool:
    return (ct or "").lower().startswith("image/")


def _guess_mime_from_ct(ct: str) -> str:
    ct = (ct or "").lower().split(";")[0].strip()
    return ct if ct.startswith("image/") else "image/jpeg"


def _to_data_url(image_bytes: bytes, mime: str) -> str:
    b64 = base64.b64encode(image_bytes).decode("ascii")
    return f"data:{mime};base64,{b64}"


# =========================
# 6) Network: download image (URL)
# =========================
async def _download_image_bytes(image_url: str) -> Tuple[bytes, str]:
    if not image_url or not isinstance(image_url, str):
        raise HTTPException(status_code=400, detail="imageUrl missing")

    async with httpx.AsyncClient(timeout=DL_TIMEOUT, follow_redirects=True) as c:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": image_url,  # 일부 서버는 Referer 체크
        }
        r = await c.get(image_url, headers=headers)

    if r.status_code != 200:
        raise HTTPException(status_code=400, detail=f"image download failed: {r.status_code}")

    ct = r.headers.get("content-type", "")
    if not _safe_content_type(ct):
        raise HTTPException(status_code=400, detail=f"not an image content-type: {ct}")

    b = r.content
    if not b or len(b) < 256:
        raise HTTPException(status_code=400, detail="image bytes empty")
    if len(b) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=400, detail=f"image too large: {len(b)} bytes")

    return b, _guess_mime_from_ct(ct)


# =========================
# 7) OpenAI Call (안전 버전)
# =========================
async def _openai_chat_json(
    system_prompt: str,
    user_content: Any,
    json_schema: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    _ensure_openai_key()

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json; charset=utf-8",
    }

    response_format: Dict[str, Any] = {"type": "json_object"}
    if json_schema:
        response_format = {"type": "json_schema", "json_schema": json_schema}

    payload = {
        "model": OPENAI_MODEL,
        "temperature": 0.2,
        "response_format": response_format,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
    }

    async with httpx.AsyncClient(timeout=OPENAI_TIMEOUT) as c:
        r = await c.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)

    if r.status_code >= 400:
        body = r.content.decode("utf-8", errors="replace")
        raise HTTPException(status_code=502, detail=f"OpenAI error: {r.status_code} {body[:500]}")

    try:
        data = r.json()
    except Exception:
        body = r.content.decode("utf-8", errors="replace")
        data = json.loads(body)

    try:
        content = data["choices"][0]["message"]["content"]
    except Exception:
        raise HTTPException(status_code=502, detail="OpenAI response missing choices[0].message.content")

    obj = _normalize_json_obj(content)

    # ✅ JSON 파싱/복구 실패 fallback 감지(운영 디버그)
    if isinstance(obj, dict) and "raw" in obj:
        head = str(obj.get("raw", ""))[:160].replace("\n", "\\n")
        print(f"[WARN] JSON_PARSE_FALLBACK model={OPENAI_MODEL} head={head}")

    return obj


# =========================
# 8) Core: Extract / Describe / QA
# =========================
def _normalize_outfit(raw: Dict[str, Any]) -> Dict[str, Any]:
    outfit = {
        "item": raw.get("item", "unknown"),
        "palette": raw.get("palette", ["unknown"]),
        "style_tags": raw.get("style_tags", ["unknown"]),
        "occasion": raw.get("occasion", ["unknown"]),
        "mood": raw.get("mood", ["unknown"]),
        "notes": raw.get("notes", []),
        "confidence": raw.get("confidence", 0.0),
    }

    if not isinstance(outfit["palette"], list):
        outfit["palette"] = ["unknown"]
    if not isinstance(outfit["style_tags"], list):
        outfit["style_tags"] = ["unknown"]
    if not isinstance(outfit["occasion"], list):
        outfit["occasion"] = ["unknown"]
    if not isinstance(outfit["mood"], list):
        outfit["mood"] = ["unknown"]
    if not isinstance(outfit["notes"], list):
        outfit["notes"] = []
    try:
        outfit["confidence"] = float(outfit["confidence"])
    except Exception:
        outfit["confidence"] = 0.0

    return outfit


async def extract_outfit_json_from_image_url(image_url: str) -> Dict[str, Any]:
    cache_key = "extract:url:" + _sha1(image_url)
    cached = CACHE_EXTRACT.get(cache_key)
    if cached:
        return cached

    img_bytes, mime = await _download_image_bytes(image_url)
    data_url = _to_data_url(img_bytes, mime)

    user_content = [
        {"type": "text", "text": EXTRACT_USER.format(schema=json.dumps(OUTFIT_JSON_SCHEMA, ensure_ascii=False))},
        {"type": "image_url", "image_url": {"url": data_url}},
    ]

    raw = await _openai_chat_json(EXTRACT_SYSTEM, user_content, json_schema=EXTRACT_JSON_SCHEMA)
    outfit = _normalize_outfit(raw)

    CACHE_EXTRACT.set(cache_key, outfit)
    return outfit


async def extract_outfit_json_from_upload(image_bytes: bytes, mime: str) -> Dict[str, Any]:
    if not image_bytes or len(image_bytes) < 256:
        raise HTTPException(status_code=400, detail="upload image bytes empty")
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=400, detail=f"image too large: {len(image_bytes)} bytes")

    h = hashlib.sha1(image_bytes).hexdigest()
    cache_key = "extract:upload:" + h
    cached = CACHE_EXTRACT.get(cache_key)
    if cached:
        return cached

    data_url = _to_data_url(image_bytes, mime)
    user_content = [
        {"type": "text", "text": EXTRACT_USER.format(schema=json.dumps(OUTFIT_JSON_SCHEMA, ensure_ascii=False))},
        {"type": "image_url", "image_url": {"url": data_url}},
    ]

    raw = await _openai_chat_json(EXTRACT_SYSTEM, user_content, json_schema=EXTRACT_JSON_SCHEMA)
    outfit = _normalize_outfit(raw)

    CACHE_EXTRACT.set(cache_key, outfit)
    return outfit


async def describe_from_outfit_json(outfit_json: Dict[str, Any]) -> Dict[str, Any]:
    key = "desc:" + _sha1(json.dumps(outfit_json, ensure_ascii=False, sort_keys=True))
    cached = CACHE_DESCRIBE.get(key)
    if cached:
        return cached

    user_prompt = DESCRIBE_USER.format(outfit_json=json.dumps(outfit_json, ensure_ascii=False))
    raw = await _openai_chat_json(DESCRIBE_SYSTEM, user_prompt, json_schema=DESCRIBE_JSON_SCHEMA)
    shaped = _coerce_describe_shape(raw)
    shaped["outfit_json"] = outfit_json

    CACHE_DESCRIBE.set(key, shaped)
    return shaped


async def describe_outfit(image_url: str) -> Dict[str, Any]:
    key = "describe:url:" + _sha1(image_url)
    cached = CACHE_DESCRIBE.get(key)
    if cached:
        return cached

    outfit = await extract_outfit_json_from_image_url(image_url)
    result = await describe_from_outfit_json(outfit)

    CACHE_DESCRIBE.set(key, result)
    return result


async def qa_from_outfit_json(outfit_json: Dict[str, Any], question: str) -> Dict[str, Any]:
    question = (question or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="question missing")

    key = "qa:" + _sha1(json.dumps(outfit_json, ensure_ascii=False, sort_keys=True) + "|" + question)
    cached = CACHE_QA.get(key)
    if cached:
        return cached

    user_prompt = QA_USER.format(
        outfit_json=json.dumps(outfit_json, ensure_ascii=False),
        question=question,
    )
    raw = await _openai_chat_json(QA_SYSTEM, user_prompt, json_schema=QA_JSON_SCHEMA)

    ans = str(raw.get("answer", "")).strip()
    try:
        conf = float(raw.get("confidence", 0.0))
    except Exception:
        conf = 0.0

    grounded_on = raw.get("grounded_on", [])
    if not isinstance(grounded_on, list):
        grounded_on = []

    out = {
        "answer": ans if ans else "추정 불가",
        "confidence": max(0.0, min(1.0, conf)),
        "grounded_on": [str(x) for x in grounded_on][:8],
    }
    CACHE_QA.set(key, out)
    return out


# =========================
# 9) FastAPI App
# =========================
app = FastAPI(
    title="LLM Outfit Server",
    default_response_class=UTF8JSONResponse,  # ✅ 전역 UTF-8
)


@app.get("/health")
async def health():
    return {"ok": True, "model": OPENAI_MODEL}


@app.post("/outfit/describe", response_model=DescribeResponse)
async def outfit_describe(req: DescribeRequest):
    # imageUrl로: 서버가 다운로드 후 OpenAI Vision 호출 (URL 403이면 upload를 쓰면 됨)
    return await describe_outfit(req.imageUrl)


@app.post("/outfit/describe_upload", response_model=DescribeResponse)
async def outfit_describe_upload(file: UploadFile = File(...)):
    # ✅ 가장 안정적인 테스트: 로컬 업로드로 403/Referer 문제 없음
    b = await file.read()
    ct = (file.content_type or "").lower()
    mime = ct.split(";")[0].strip() if ct.startswith("image/") else "image/jpeg"

    outfit = await extract_outfit_json_from_upload(b, mime)
    return await describe_from_outfit_json(outfit)


@app.post("/outfit/qa", response_model=QAResponse)
async def outfit_qa(req: QARequest):
    return await qa_from_outfit_json(req.outfit_json, req.question)


@app.exception_handler(Exception)
async def all_exception_handler(_, exc: Exception):
    # 서버 안전 에러 (기본 JSONResponse는 ascii escape로 보일 수 있으니 UTF8JSONResponse로 고정)
    return UTF8JSONResponse(status_code=500, content={"error": repr(exc)})


# 실행:
# $env:OPENAI_API_KEY="sk-proj-..."
# $env:OPENAI_MODEL="gpt-4o-mini"
# uvicorn llm_server:app --reload --host 127.0.0.1 --port 8001
