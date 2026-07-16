from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import Settings
from .nvidia_client import NvidiaClient, NvidiaError
from .style import build_style_profile, choose_reference_samples, theme_guide


@dataclass
class DraftResult:
    content: str
    image_analysis: str
    style_profile: str
    used_remote_model: bool


def _photo_notes_text(photo_notes: list[str]) -> str:
    return "\n".join(
        f"- 사진 {index + 1}: {note.strip() or '(메모 없음)'}" for index, note in enumerate(photo_notes)
    ) or "(사진 없음)"


def _local_outline(topic: str, memo: str, photo_notes: list[str], theme: str) -> str:
    title = topic.strip() or "오늘 기록"
    headings = (
        ("방문하게 된 계기", "매장 분위기와 접근성", "메뉴와 사진 기록", "먹어본 후기", "마무리")
        if theme in ("맛집 후기", "카페")
        else ("시작하며", "사진으로 남긴 순간", "느낀 점", "마무리")
    )
    lines = ["# 제목 후보", f"1. {title}", f"2. {title} 솔직 후기", f"3. 사진으로 남긴 {title}", "", "# 글 구성"]
    for heading in headings:
        lines.append(f"- ## {heading}: {memo.strip() or '제공한 메모와 사진을 바탕으로 작성'}")
    for index, note in enumerate(photo_notes, start=1):
        lines.append(f"- [사진 {index} 삽입]: {note.strip() or '사진 설명 추가 필요'}")
    lines.extend(["", "# 확인 필요", "- 주소, 가격, 영업시간 등 사진·메모에 없는 정보는 발행 전에 직접 입력"])
    return "\n".join(lines)


def _local_body(topic: str, memo: str, photo_notes: list[str], style_profile: str, theme: str, outline: str) -> str:
    title = topic.strip() or "오늘 기록"
    section_title = "방문하게 된 계기" if theme in ("맛집 후기", "카페", "여행") else "시작하며"
    photo_section = "메뉴와 사진 기록" if theme in ("맛집 후기", "카페") else "사진으로 남긴 순간"
    lines = [
        f"# {title}",
        "",
        f"## {section_title}",
        memo.strip() or "오늘의 기록을 사진과 함께 남겨본다.",
        "",
        f"## {photo_section}",
    ]
    if photo_notes:
        for index, note in enumerate(photo_notes, start=1):
            lines.extend(["", f"[사진 {index} 삽입]", note.strip() or "사진 속 분위기와 느낀 점을 여기에 적어 주세요."])
    else:
        lines.append("사진을 추가하면 사진별 설명 문단이 생성됩니다.")
    lines.extend(
        [
            "",
            "## 마무리",
            "이 글은 NVIDIA API 키 없이 만든 로컬 본문입니다. 설정에서 API 키를 저장하면 사진 분석과 말투 반영 결과를 받을 수 있습니다.",
            "",
            "#기록 #블로그초안",
            "",
            "## 확인 필요",
            "- 장소 정보와 가격 등 사실 정보를 발행 전에 확인해 주세요.",
            "",
            f"<!-- outline: {outline[:300]} -->",
            f"<!-- {style_profile} -->",
        ]
    )
    return "\n".join(lines)


def _context(topic: str, memo: str, photo_notes: list[str], style_samples: str, theme: str, image_analysis: str) -> tuple[str, str]:
    style_profile = build_style_profile(style_samples, theme)
    references = choose_reference_samples(style_samples, topic)
    references_text = "\n\n--- 예시 글 ---\n".join(references) if references else "(제공된 예시 없음)"
    context = f"""
[주제]
{topic or '사용자 기록'}

[선택 테마]
{theme}

[테마 작성 가이드]
{theme_guide(theme)}

[사용자 메모]
{memo or '(없음)'}

[사진별 사용자 메모]
{_photo_notes_text(photo_notes)}

[사진 분석]
{image_analysis}

[말투 프로필]
{style_profile}

[참고할 기존 글 일부]
{references_text}
""".strip()
    return context, style_profile


def generate_outline(
    settings: Settings,
    topic: str,
    memo: str,
    photos: list[Path],
    photo_notes: list[str],
    style_samples: str,
    theme: str = "직접 입력",
) -> DraftResult:
    """Create an editable factual plan before generating the finished post."""
    style_profile = build_style_profile(style_samples, theme)
    client = NvidiaClient(settings)
    try:
        image_analysis = client.analyze_images(photos, photo_notes)
        if not client.enabled:
            return DraftResult(_local_outline(topic, memo, photo_notes, theme), image_analysis, style_profile, False)

        context, style_profile = _context(topic, memo, photo_notes, style_samples, theme, image_analysis)
        prompt = f"""
당신은 정확성을 우선하는 한국어 블로그 편집자입니다. 아래 자료를 바탕으로 완성 본문 전에 사용자가 검토·수정할 수 있는 글 설계안을 Markdown으로 작성하세요.

[반드시 지킬 원칙]
- 제공한 메모와 사진 분석 밖의 사실은 만들지 않습니다.
- 기존 글 예시의 문장은 복사하지 않고, 말투와 문단 호흡만 참고합니다.
- 광고성 과장이나 허위 후기를 쓰지 않습니다.

{context}

[출력 형식]
# 제목 후보 (3개)
# 글 구성 (소제목 3~5개와 각 문단에서 다룰 사실)
# 사진 배치 (각 [사진 N 삽입]과 캡션 방향)
# 확인 필요 (사용자가 채워야 할 정보)
""".strip()
        content = client.chat(
            settings.writer_model,
            [{"role": "system", "content": "사실 검증과 사용자 문체를 우선하는 한국어 블로그 기획 도우미입니다."}, {"role": "user", "content": prompt}],
            max_tokens=1500,
            temperature=0.45,
        )
        return DraftResult(content, image_analysis, style_profile, True)
    except NvidiaError as error:
        return DraftResult(
            f"[NVIDIA 모델 호출 실패: {error}]\n\n{_local_outline(topic, memo, photo_notes, theme)}",
            f"사진 분석 실패: {error}",
            style_profile,
            False,
        )


def generate_body(
    settings: Settings,
    topic: str,
    memo: str,
    photos: list[Path],
    photo_notes: list[str],
    style_samples: str,
    theme: str,
    outline: str,
    image_analysis: str = "",
) -> DraftResult:
    """Expand the reviewed outline into a ready-to-edit blog body."""
    style_profile = build_style_profile(style_samples, theme)
    client = NvidiaClient(settings)
    try:
        if not image_analysis:
            image_analysis = client.analyze_images(photos, photo_notes)
        if not client.enabled:
            return DraftResult(_local_body(topic, memo, photo_notes, style_profile, theme, outline), image_analysis, style_profile, False)

        context, style_profile = _context(topic, memo, photo_notes, style_samples, theme, image_analysis)
        prompt = f"""
당신은 한국어 블로그 편집자입니다. 사용자가 검토한 설계안을 따라 네이버 블로그에 붙여 넣을 수 있는 완성 본문을 Markdown으로 작성하세요.

[반드시 지킬 원칙]
- 제공한 사실, 사용자 메모, 사진 분석과 설계안만 근거로 작성합니다.
- 사진에서 보이지 않는 가격, 주소, 영업시간, 제품명, 인물 관계, 경험을 지어내지 않습니다.
- 기존 예시의 문장을 복사하지 말고 말투와 구성 습관만 참고합니다.
- HTML 표나 코드 블록은 사용하지 않습니다.

{context}

[사용자가 검토한 설계안]
{outline or '(설계안 없음)'}

[출력 형식]
1. 선택한 제목 한 개로 시작합니다.
2. ## 소제목 2~5개 아래에 자연스러운 완성 문단을 씁니다.
3. 각 사진 위치에 정확히 '[사진 N 삽입]'을 넣고 바로 아래에 사진 설명 문단을 씁니다.
4. 끝에는 해시태그 5~10개와 '## 확인 필요' 목록을 넣습니다.
""".strip()
        content = client.chat(
            settings.writer_model,
            [{"role": "system", "content": "정확성과 사용자의 문체를 우선하는 한국어 블로그 작성 도우미입니다."}, {"role": "user", "content": prompt}],
            max_tokens=2600,
            temperature=0.62,
        )
        return DraftResult(content, image_analysis, style_profile, True)
    except NvidiaError as error:
        fallback = _local_body(topic, memo, photo_notes, style_profile, theme, outline)
        return DraftResult(f"[NVIDIA 모델 호출 실패: {error}]\n\n{fallback}", image_analysis or f"사진 분석 실패: {error}", style_profile, False)


def generate_draft(
    settings: Settings,
    topic: str,
    memo: str,
    photos: list[Path],
    photo_notes: list[str],
    style_samples: str,
    theme: str = "직접 입력",
) -> DraftResult:
    """Backward-compatible one-call body generation for integrations using the old API."""
    outline = generate_outline(settings, topic, memo, photos, photo_notes, style_samples, theme)
    return generate_body(
        settings,
        topic,
        memo,
        photos,
        photo_notes,
        style_samples,
        theme,
        outline.content,
        outline.image_analysis,
    )
