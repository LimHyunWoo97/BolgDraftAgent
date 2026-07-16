from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path


# In a PyInstaller build, keep the editable .env next to BlogDraftAgent.exe
# instead of inside PyInstaller's read-only _internal package directory.
ROOT_DIR = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent
ENV_PATH = ROOT_DIR / ".env"


def _read_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


@dataclass
class Settings:
    nvidia_api_key: str = ""
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    vision_model: str = "meta/llama-3.2-11b-vision-instruct"
    writer_model: str = "nvidia/llama-3.3-nemotron-super-49b-v1.5"
    naver_client_id: str = ""
    naver_client_secret: str = ""
    naver_redirect_uri: str = "http://127.0.0.1:8765/callback"

    @classmethod
    def load(cls) -> "Settings":
        file_values = _read_env(ENV_PATH)

        def value(key: str, default: str = "") -> str:
            return os.getenv(key, file_values.get(key, default))

        return cls(
            nvidia_api_key=value("NVIDIA_API_KEY"),
            nvidia_base_url=value("NVIDIA_BASE_URL", cls.nvidia_base_url),
            vision_model=value("NVIDIA_VISION_MODEL", cls.vision_model),
            writer_model=value("NVIDIA_WRITER_MODEL", cls.writer_model),
            naver_client_id=value("NAVER_CLIENT_ID"),
            naver_client_secret=value("NAVER_CLIENT_SECRET"),
            naver_redirect_uri=value("NAVER_REDIRECT_URI", cls.naver_redirect_uri),
        )

    def save(self) -> None:
        """Save local credentials in .env, which is intentionally git-ignored."""
        lines = [
            "# Local-only configuration. Do not commit this file.",
            f"NVIDIA_API_KEY={self.nvidia_api_key}",
            f"NVIDIA_BASE_URL={self.nvidia_base_url}",
            f"NVIDIA_VISION_MODEL={self.vision_model}",
            f"NVIDIA_WRITER_MODEL={self.writer_model}",
            f"NAVER_CLIENT_ID={self.naver_client_id}",
            f"NAVER_CLIENT_SECRET={self.naver_client_secret}",
            f"NAVER_REDIRECT_URI={self.naver_redirect_uri}",
            "",
        ]
        ENV_PATH.write_text("\n".join(lines), encoding="utf-8")
