from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import Settings
from .nvidia_client import NvidiaClient, NvidiaError
from .style import build_style_profile, choose_reference_samples


@dataclass
class DraftResult:
    content: str
    image_analysis: str
    style_profile: str
    used_remote_model: bool


def _local_draft(topic: str, memo: str, photo_notes: list[str], style_profile: str) -> str:
    title = topic.strip() or "오늘 기록"
    lines = [
        f"# {title}",
        "",
        "## 시작하며",
        memo.strip() or "오늘의 기록을 사진과 함께 남겨본다.",
        "",
        "## 사진으로 남긴 순간",
    ]
    if photo_notes:
        for index, note in enumerate(photo_notes, start=1):
            lines.extend(
                [
                    "",
                    f"[사진 {index} 삽입]",
                    f"사진 설명: {note.strip() or '사진 속 분위기와 느낀 점을 여기에 적어 주세요.'}",
                ]
            )
    else:
        lines.append("사진을 추가하면 사진별 설명 문단이 생성됩니다.")
    lines.extend(
        [
            "",
            "## 마무리",
            "이 글은 NVIDIA API 키 없이 만든 로컬 초안입니다. 설정에서 API 키를 저장하면 사진 분석과 말투 반영 초안을 생성할 수 있습니다.",
            "",
            "#기록 #블로그초안",
            "",
            f"<!-- {style_profile} -->",
        ]
    )
    return "\n".join(lines)


def generate_draft(
    settings: Settings,
    topic: str,
    memo: str,
    photos: list[Path],
    photo_notes: list[str],
    style_samples: str,
) -> DraftResult:
    style_profile = build_style_profile(style_samples)
    client = NvidiaClient(settings)

    try:
        image_analysis = client.analyze_images(photos, photo_notes)
        if not client.enabled:
            return DraftResult(
                content=_local_draft(topic, memo, photo_notes, style_profile),
                image_analysis=image_analysis,
                style_profile=style_profile,
                used_remote_model=False,
            )

        references = choose_reference_samples(style_samples, topic)
        references_text = "\n\n--- 예시 글 ---\n".join(references) if references else "(제공된 예시 없음)"
        photo_notes_text = "\n".join(
            f"- 사진 {index + 1}: {note.strip() or '(메모 없음)'}" for index, note in enumerate(photo_notes)
        ) or "(사진 없음)"
        prompt = f"""
당신은 한국어 블로그 편집자입니다. 사용자의 말투를 반영해 네이버 블로그에 붙여 넣을 수 있는 Markdown 초안을 작성하세요.

[반드시 지킬 원칙]
- 제공한 사실, 사용자 메모, 사진 분석 결과만 근거로 작성합니다.
- 사진에서 보이지 않는 가격, 주소, 영업시간, 제품명, 인물 관계, 경험을 지어내지 않습니다.
- 확실하지 않은 정보는 본문에 쓰지 말고 끝의 '확인 필요' 목록에 둡니다.
- 기존 예시의 문장을 복사하지 말고 말투와 구성 습관만 참고합니다.
- 광고성 과장, 검색 순위 보장, 허위 후기는 쓰지 않습니다.
- HTML 표나 코드 블록은 사용하지 않습니다.

[주제]
{topic or '사용자 기록'}

[사용자 메모]
{memo or '(없음)'}

[사진별 사용자 메모]
{photo_notes_text}

[사진 분석]
{image_analysis}

[말투 프로필]
{style_profile}

[참고할 기존 글 일부]
{references_text}

[출력 형식]
1. 맨 위에 제목 후보 3개를 번호로 제안합니다.
2. 그 아래 '---' 이후 선택한 제목으로 완성된 본문을 작성합니다.
3. 본문에는 ## 소제목을 2~4개 넣습니다.
4. 각 사진 위치에는 정확히 '[사진 N 삽입]'을 넣고 바로 아래에 자연스러운 사진 설명을 씁니다.
5. 끝에는 해시태그 5~10개와 '## 확인 필요' 목록을 넣습니다.
""".strip()
        content = client.chat(
            settings.writer_model,
            [
                {"role": "system", "content": "정확성과 사용자의 문체를 우선하는 한국어 블로그 작성 도우미입니다."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=2300,
            temperature=0.65,
        )
        return DraftResult(content, image_analysis, style_profile, True)
    except NvidiaError as error:
        fallback = _local_draft(topic, memo, photo_notes, style_profile)
        return DraftResult(
            content=f"[NVIDIA 모델 호출 실패: {error}]\n\n{fallback}",
            image_analysis=f"사진 분석 실패: {error}",
            style_profile=style_profile,
            used_remote_model=False,
        )
