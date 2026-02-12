# (use_nickname 결정) 닉네임 확률 정책
import random

from .guards import extract_choice_number, is_help_query, is_greeting, is_choice_question


def decide_use_nickname(nickname: str, text: str, followup_prob: float = 0.40) -> bool:
    nick = (nickname or "").strip()
    if not nick:
        return False

    t = (text or "").strip()

    # 번호 지정 / 선택질문 / 베스트 요청은 확정
    is_number_pick = extract_choice_number(t) is not None
    is_choice = is_choice_question(t)  # "몇번입을까" 같은 류
    is_recommend_one = ("제일" in t) or ("하나만" in t) or ("베스트" in t)

    # 인사/도움말은 확정(초반 UX)
    is_first_like = is_greeting(t) or is_help_query(t)

    if is_number_pick or is_choice or is_recommend_one or is_first_like:
        return True

    # 이후는 확률
    return random.random() < followup_prob
