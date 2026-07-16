from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


THEMES = ("맛집 후기", "카페", "여행", "제품 리뷰", "일상·정보", "직접 입력")
PROFILE_PATH = Path(__file__).resolve().parent.parent / ".style_profiles.json"


@dataclass
class ThemeProfileStore:
    """Local-only style samples, intentionally kept outside the Git repository."""

    path: Path = PROFILE_PATH

    def load(self, theme: str) -> str:
        if not self.path.exists():
            return ""
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return ""
        return str(data.get(theme, ""))

    def save(self, theme: str, samples: str) -> None:
        data: dict[str, str] = {}
        if self.path.exists():
            try:
                raw = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    data = {str(key): str(value) for key, value in raw.items()}
            except (OSError, json.JSONDecodeError):
                pass
        data[theme] = samples.strip()
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
