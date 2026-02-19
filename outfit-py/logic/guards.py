# (_is_fashion_query / _is_help_query / _is_greeting)

import re
from typing import Optional

# ----------------------------
# normalize
# ----------------------------
def norm(text: str) -> str:
    t = (text or "").strip().lower()
    t = re.sub(r"\s+", "", t)
    return t


# ----------------------------
# greeting
# ----------------------------
HELLO_PAT = re.compile(r"^(hi|hello|hey|하이|안녕(하세요)?|여보세요|헬로)\b", re.I)

def is_greeting(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return False
    if HELLO_PAT.search(t):
        return True
    if t in {"?", "??", "ㅋ", "ㅎㅎ", "ㅎ", "ㅇㅇ", "ㅇㅋ"}:
        return True
    if len(t) <= 6 and any(x in t.lower() for x in ["안녕", "여보", "hi", "hello", "hey", "ㅎㅇ", "하이", "하2"]):
        return True
    return False


# ----------------------------
# help / identity / usage
# ----------------------------
HELP_PATTERNS = [
    r"^누구냐넌$",
    r"^넌누구야$",
    r"^너는누구야$",
    r"^너누구야$",
    r"^너누구냐$",
    r"^너뭐야$",
    r"^너뭔데$",
    r"^너머야$",
    r"^너뭐임$",
    r"^정체뭐야$",
    r"^정체가뭐야$",
    r"assistant|어시스턴트|봇|챗봇|ai",
    r"이앱뭐야|이거뭐야|여기뭐야|서비스뭐야|프로그램뭐야|사이트뭐야",
    r"어떻게써|어케써|어떻게사용|사용법|사용방법|가이드|도움말|help",
]
HELP_RE = re.compile("|".join(f"(?:{p})" for p in HELP_PATTERNS), re.I)

def is_help_query(text: str) -> bool:
    t = norm(text)
    if not t:
        return False

    if HELP_RE.search(t):
        return True

    if "너" in t and (("누구" in t) or ("뭐" in t) or ("정체" in t)):
        return True

    if any(k in t for k in ["사용", "방법", "어떻게", "어케", "help", "가이드", "도움말"]):
        if any(k in t for k in ["앱", "서비스", "이거", "여기", "프로그램", "사이트", "너", "봇", "ai"]):
            return True

    # 닉네임/정체성 입력도 help로 흡수 (원하면 더 정교화 가능)
    if any(x in t for x in ["나", "내", "닉", "닉네임"]) and any(x in t for x in ["이름", "입니다", "야"]):
        return True

    return False


# ----------------------------
# number / ordinal extraction
# ----------------------------
NUM_PAT = re.compile(r"(?:(\d)\s*번)|(?:^(\d)$)")

ORDINAL_MAP = {
    "첫번째": 1, "첫째": 1, "1번째": 1,
    "두번째": 2, "둘째": 2, "2번째": 2,
    "세번째": 3, "셋째": 3, "3번째": 3,
    "네번째": 4, "넷째": 4, "4번째": 4,
    "다섯번째": 5, "5번째": 5,
    "여섯번째": 6, "6번째": 6,
    "일곱번째": 7, "7번째": 7,
    "여덟번째": 8, "8번째": 8,
}

def extract_choice_number(text: str) -> Optional[int]:
    t = (text or "").strip().lower()
    if not t:
        return None

    m = NUM_PAT.search(t)
    if m:
        d = m.group(1) or m.group(2)
        if d and d.isdigit():
            n = int(d)
            if 1 <= n <= 8:
                return n

    for k, v in ORDINAL_MAP.items():
        if k in t:
            return v

    return None


# ----------------------------
# fashion detectors
# ----------------------------
FASHION_KEYWORDS = [
    "코디", "패션", "옷", "착장", "룩", "스타일", "스타일링", "핏", "무드",
    "상의", "하의", "아우터", "자켓", "코트", "신발", "운동화", "가방",
    "색", "컬러", "블랙", "화이트", "베이지", "브라운", "네이비",
    "데일리룩", "스트릿", "미니멀", "캐주얼", "포멀", "오피스룩", "데이트룩",
    "코디추천", "룩북", "스냅", "ootd",
    "이거 어울려", "매치", "조합", "어떻게 입", "뭐 입", "뭐입", "설명해줘",
]

EVAL_WORDS = [
    "별로", "구려", "애매", "괜찮", "좋", "맘에", "싫", "취향", "추천", "이유",
    "뭐가", "나아", "더좋", "고르", "골라", "선택", "비교", "추천왜", "왜이래",
    "다시", "다른", "바꿔", "바뀌", "이상", "실망", "최악", "별론데",
]

BODY_WORDS = [
    "키", "작아", "작은", "크", "큰", "하체", "상체", "어깨", "골반", "허리",
    "통통", "뚱", "마른", "슬림", "체형", "다리", "팔", "비율",
]

TPO_WORDS = [
    "면접", "출근", "오피스", "하객", "데이트", "결혼식", "소개팅", "여행",
    "모임", "행사", "졸업식", "입학식",
    "봄", "여름", "가을", "겨울", "환절기", "비오는날", "추워", "더워",
]

COLOR_WORDS = [
    "검정", "블랙", "화이트", "흰", "베이지", "브라운", "네이비", "그레이", "회색", "차콜",
    "파랑", "블루", "초록", "그린", "빨강", "레드", "버건디", "색", "컬러",
]

CHOICE_Q_PAT = re.compile(r"(몇\s*번|어느\s*(게|것)|뭐\s*가\s*좋|뭐\s*입|뭘\s*입|뭐\s*입지|고를까|골라|선택)")

def is_choice_question(text: str) -> bool:
    t = (text or "").strip().lower()
    if not t:
        return False
    if CHOICE_Q_PAT.search(t):
        return True
    if ("번" in t) and (extract_choice_number(t) is None) and ("몇" in t or "어느" in t or "뭐" in t):
        return True
    return False


def is_fashion_query(text: str) -> bool:
    t = (text or "").strip().lower()
    if not t:
        return False

    if is_choice_question(t):
        return True
    if extract_choice_number(t) is not None:
        return True
    if any(w in t for w in EVAL_WORDS):
        return True
    if any(w in t for w in BODY_WORDS) or any(w in t for w in TPO_WORDS):
        return True
    if any(w in t for w in COLOR_WORDS):
        return True
    for kw in FASHION_KEYWORDS:
        if kw in t:
            return True
    return False
