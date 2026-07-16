from __future__ import annotations

import re
from collections import Counter


ENDING_PATTERN = re.compile(r"[가-힣]+(?:습니다|어요|네요|까요|죠|다)(?=[.!?\n]|$)")
EMOJI_PATTERN = re.compile(r"[😀-🙏✨⭐💡📌✅❗❤️👍😊😂🥹🙌🔥💬]")


def build_style_profile(samples: str) -> str:
    """Build a transparent, editable style card without sending data to a model."""
    cleaned = "\n".join(line.strip() for line in samples.splitlines() if line.strip())
    if not cleaned:
        return (
            "말투 프로필: 친절한 한국어 존댓말. 짧은 문단으로 핵심을 설명하고, "
            "과장된 홍보 문구나 확인되지 않은 사실은 쓰지 않는다."
        )

    sentences = [s.strip() for s in re.split(r"[.!?\n]+", cleaned) if s.strip()]
    average_length = round(sum(len(s) for s in sentences) / max(len(sentences), 1))
    ending_words = ENDING_PATTERN.findall(cleaned)
    endings = Counter(word[-3:] for word in ending_words if len(word) >= 3).most_common(3)
    ending_summary = ", ".join(part for part, _ in endings) or "일관된 문장 끝맺음"
    emoji_count = len(EMOJI_PATTERN.findall(cleaned))
    tone = "친근한 구어체" if any(x in cleaned for x in ("ㅎㅎ", "ㅋㅋ", "~", "요!")) else "차분한 설명체"
    emoji_rule = "이모지를 가끔 사용" if emoji_count >= 2 else "이모지는 필요할 때만 사용"

    return (
        f"말투 프로필: {tone}. 문장은 평균 {average_length}자 정도로 쓴다. "
        f"자주 쓰는 끝맺음 특징: {ending_summary}. {emoji_rule}. "
        "제공된 예시의 분위기는 따르되 문장을 그대로 복사하지 않는다."
    )


def choose_reference_samples(samples: str, topic: str, limit: int = 3) -> list[str]:
    """A dependency-free first-pass RAG: rank paragraphs by topic word overlap."""
    keywords = {word.lower() for word in re.findall(r"[가-힣A-Za-z0-9]{2,}", topic)}
    blocks = [block.strip() for block in re.split(r"\n\s*\n", samples) if block.strip()]

    def score(block: str) -> tuple[int, int]:
        words = {word.lower() for word in re.findall(r"[가-힣A-Za-z0-9]{2,}", block)}
        return (len(keywords & words), min(len(block), 1200))

    ranked = sorted(blocks, key=score, reverse=True)
    return [block[:1200] for block in ranked[:limit]]
