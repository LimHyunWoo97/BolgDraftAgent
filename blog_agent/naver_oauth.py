from __future__ import annotations

import json
import secrets
import threading
import webbrowser
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen

from .config import Settings


@dataclass
class NaverProfile:
    nickname: str
    email: str = ""


class NaverLogin:
    """Official OAuth login for app identity only; it intentionally cannot publish posts."""

    def __init__(self, settings: Settings):
        self.settings = settings

    def start(self, callback) -> None:
        if not self.settings.naver_client_id or not self.settings.naver_client_secret:
            callback(None, "NAVER_CLIENT_ID와 NAVER_CLIENT_SECRET을 설정에서 입력해 주세요.")
            return

        parsed = urlparse(self.settings.naver_redirect_uri)
        if parsed.hostname not in {"127.0.0.1", "localhost"} or not parsed.port:
            callback(None, "이 MVP는 localhost 콜백 URL만 지원합니다. 예: http://127.0.0.1:8765/callback")
            return

        state = secrets.token_urlsafe(24)

        def run() -> None:
            try:
                profile = self._run_callback_server(parsed.hostname, parsed.port, parsed.path, state)
                callback(profile, None)
            except Exception as error:  # user-facing background task boundary
                callback(None, str(error))

        threading.Thread(target=run, daemon=True).start()
        query = urlencode(
            {
                "response_type": "code",
                "client_id": self.settings.naver_client_id,
                "redirect_uri": self.settings.naver_redirect_uri,
                "state": state,
            }
        )
        webbrowser.open(f"https://nid.naver.com/oauth2.0/authorize?{query}")

    def _run_callback_server(self, host: str, port: int, callback_path: str, expected_state: str) -> NaverProfile:
        result: dict[str, str] = {}

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802 - required by BaseHTTPRequestHandler
                request_path = urlparse(self.path)
                if request_path.path != callback_path:
                    self.send_error(404)
                    return
                values = parse_qs(request_path.query)
                result["code"] = values.get("code", [""])[0]
                result["state"] = values.get("state", [""])[0]
                result["error"] = values.get("error", [""])[0]
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(
                    "<h2>로그인 확인이 완료되었습니다.</h2><p>이 창을 닫고 Blog Draft Agent로 돌아가세요.</p>".encode("utf-8")
                )

            def log_message(self, format, *args):  # noqa: A002
                return

        server = HTTPServer((host, port), Handler)
        server.timeout = 180
        server.handle_request()
        if result.get("error"):
            raise RuntimeError(f"네이버 로그인 취소 또는 오류: {result['error']}")
        if not result.get("code") or result.get("state") != expected_state:
            raise RuntimeError("네이버 로그인 상태 검증에 실패했습니다.")

        token_query = urlencode(
            {
                "grant_type": "authorization_code",
                "client_id": self.settings.naver_client_id,
                "client_secret": self.settings.naver_client_secret,
                "code": result["code"],
                "state": expected_state,
            }
        )
        with urlopen(f"https://nid.naver.com/oauth2.0/token?{token_query}", timeout=30) as response:
            token_payload = json.loads(response.read().decode("utf-8"))
        access_token = token_payload.get("access_token")
        if not access_token:
            raise RuntimeError("네이버 액세스 토큰을 받지 못했습니다.")

        request = Request(
            "https://openapi.naver.com/v1/nid/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        with urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
        profile = payload.get("response", {})
        return NaverProfile(nickname=profile.get("nickname") or "네이버 사용자", email=profile.get("email", ""))
