from __future__ import annotations

import base64
import json
import mimetypes
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .config import Settings


class NvidiaError(RuntimeError):
    pass


class NvidiaClient:
    """Small OpenAI-compatible client for NVIDIA Build or a self-hosted NIM."""

    def __init__(self, settings: Settings):
        self.settings = settings

    @property
    def enabled(self) -> bool:
        return bool(self.settings.nvidia_api_key.strip())

    def chat(self, model: str, messages: list[dict], max_tokens: int = 1800, temperature: float = 0.55) -> str:
        if not self.enabled:
            raise NvidiaError("NVIDIA_API_KEY가 설정되지 않았습니다.")

        url = self.settings.nvidia_base_url.rstrip("/") + "/chat/completions"
        body = json.dumps(
            {
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            },
            ensure_ascii=False,
        ).encode("utf-8")
        request = Request(
            url,
            data=body,
            headers={
                "Authorization": f"Bearer {self.settings.nvidia_api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=120) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            message = error.read().decode("utf-8", errors="replace")
            raise NvidiaError(f"NVIDIA API 오류 ({error.code}): {message[:500]}") from error
        except URLError as error:
            raise NvidiaError(f"NVIDIA API 연결 실패: {error.reason}") from error

        try:
            content = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise NvidiaError(f"NVIDIA API 응답 형식이 예상과 다릅니다: {payload}") from error
        if not content:
            raise NvidiaError("NVIDIA 모델이 빈 응답을 반환했습니다.")
        return str(content).strip()

    @staticmethod
    def image_part(path: Path) -> dict:
        if path.stat().st_size > 8 * 1024 * 1024:
            raise NvidiaError(f"{path.name}: 8MB를 초과해 전송하지 않았습니다. 사진 크기를 줄여 주세요.")
        mime_type = mimetypes.guess_type(path.name)[0] or "image/jpeg"
        if mime_type not in {"image/jpeg", "image/png", "image/gif", "image/webp"}:
            raise NvidiaError(f"{path.name}: JPG, PNG, GIF, WEBP 이미지만 지원합니다.")
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        return {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{encoded}"}}

    def analyze_images(self, photos: list[Path], notes: list[str]) -> str:
        if not photos:
            return "업로드된 사진이 없습니다."
        if not self.enabled:
            return "NVIDIA API 키가 없어 사진 분석은 건너뛰었습니다. 사진 메모를 기반으로 초안을 만듭니다."

        parts: list[dict] = [
            {
                "type": "text",
                "text": (
                    "사진을 블로그 초안용으로 분석해 주세요. 사진별로 실제로 보이는 요소, "
                    "분위기, 안전한 캡션 후보를 한국어로 2~3문장씩 작성하세요. "
                    "보이지 않는 가격·주소·영업시간·인물 관계 등은 추측하지 마세요."
                ),
            }
        ]
        for index, photo in enumerate(photos):
            note = notes[index] if index < len(notes) else ""
            parts.append({"type": "text", "text": f"\n[사진 {index + 1}: {photo.name}] 사용자 메모: {note or '(없음)'}"})
            parts.append(self.image_part(photo))

        return self.chat(
            self.settings.vision_model,
            [{"role": "user", "content": parts}],
            max_tokens=1400,
            temperature=0.2,
        )
