from __future__ import annotations

import re
from collections import Counter


ENDING_PATTERN = re.compile(r"[가-힣]+(?:습니다|이에요|예요|인데요|같아요|거예요|까요|세요)(?=[.!?\n]|$)")
EMOJI_PATTERN = re.compile(r"[\U0001F300-\U0001FAFF⭐❤♥♡☺]", re.UNICODE)

THEME_GUIDES = {
    "맛집 후기": (
        "1인칭 방문 후기형 맛집 글입니다. 첫 문단은 방문 계기와 매장 위치·접근성을 자연스럽게 소개합니다. "
        "매장 분위기, 메뉴/가격, 기본찬, 주문 메뉴, 맛의 포인트, 편의시설 순서로 사진 흐름에 맞춰 전개합니다. "
        "짧은 문단과 '인데요', '같아요', '좋을 것 같습니다' 같은 친근한 존댓말을 사용합니다. "
        "확인한 정보만 쓰고, 맛 평가는 개인 경험임을 유지합니다."
    ),
    "카페": "방문 계기, 공간/좌석, 메뉴, 주문 음료·디저트, 맛과 분위기, 재방문 포인트를 부드러운 후기형 문장으로 작성합니다.",
    "여행": "이동 동선과 시간 흐름을 따라 장소의 분위기, 실제 경험, 팁, 사진 포인트를 기록형 문체로 작성합니다.",
    "제품 리뷰": "사용 목적, 개봉/외관, 핵심 기능, 실제 사용감, 장단점, 추천 대상 순서로 과장 없이 검증 가능한 정보 중심으로 작성합니다.",
    "일상·정보": "짧은 도입 뒤 경험과 핵심 정보를 읽기 쉽게 나누고, 독자가 바로 활용할 수 있는 팁으로 마무리합니다.",
    "직접 입력": "사용자가 제공한 샘플의 문장 길이와 어미, 문단 구성만 참고합니다.",
}


def theme_guide(theme: str) -> str:
    return THEME_GUIDES.get(theme, THEME_GUIDES["직접 입력"])


def build_style_profile(samples: str, theme: str = "직접 입력") -> str:
    """Build a transparent, editable style card without copying source posts."""
    cleaned = "\n".join(line.strip() for line in samples.splitlines() if line.strip())
    guide = theme_guide(theme)
    if not cleaned:
        return f"테마: {theme}. {guide} 샘플 글이 없으므로 위 테마 가이드만 적용합니다."

    sentences = [sentence.strip() for sentence in re.split(r"[.!?\n]+", cleaned) if sentence.strip()]
    average_length = round(sum(len(sentence) for sentence in sentences) / max(len(sentences), 1))
    ending_words = ENDING_PATTERN.findall(cleaned)
    endings = Counter(word[-4:] for word in ending_words if len(word) >= 4).most_common(3)
    ending_summary = ", ".join(part for part, _ in endings) or "서술형 종결"
    emoji_count = len(EMOJI_PATTERN.findall(cleaned))
    tone = "친근한 구어체 존댓말" if any(token in cleaned for token in ("인데요", "같아요", "ㅎㅎ", "?!")) else "차분한 설명형 존댓말"
    emoji_rule = "이모지는 문단당 1개 이하로 가볍게 사용" if emoji_count >= 2 else "이모지는 꼭 필요할 때만 사용"

    return (
        f"테마: {theme}. 테마 구성: {guide} 사용자 말투: {tone}. "
        f"문장은 평균 {average_length}자 안팎으로 짧게 끊습니다. 선호 어미: {ending_summary}. {emoji_rule}. "
        "샘플의 사실·고유 표현·문장을 복사하지 말고, 말투와 문단 호흡만 반영합니다."
    )


def choose_reference_samples(samples: str, topic: str, limit: int = 3) -> list[str]:
    """Dependency-free first-pass RAG: rank paragraphs by topic-word overlap."""
    keywords = {word.lower() for word in re.findall(r"[가-힣A-Za-z0-9]{2,}", topic)}
    blocks = [block.strip() for block in re.split(r"\n\s*\n", samples) if block.strip()]

    def score(block: str) -> tuple[int, int]:
        words = {word.lower() for word in re.findall(r"[가-힣A-Za-z0-9]{2,}", block)}
        return (len(keywords & words), min(len(block), 1200))

    ranked = sorted(blocks, key=score, reverse=True)
    return [block[:1200] for block in ranked[:limit]]
