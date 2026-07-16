from __future__ import annotations

import json
import secrets
import threading
import time
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
    """OAuth authorization-code login using a local loopback callback server."""

    def __init__(self, settings: Settings):
        self.settings = settings

    def start(self, callback) -> None:
        if not self.settings.naver_client_id or not self.settings.naver_client_secret:
            callback(None, "NAVER Client ID와 Client Secret을 설정에 모두 입력해 주세요.")
            return

        parsed = urlparse(self.settings.naver_redirect_uri)
        if parsed.hostname not in {"127.0.0.1", "localhost"} or not parsed.port or not parsed.path:
            callback(None, "Redirect URI는 http://127.0.0.1:8765/callback 형식으로 입력해 주세요.")
            return

        state = secrets.token_urlsafe(24)
        try:
            server, result = self._create_callback_server(parsed.hostname, parsed.port, parsed.path)
        except OSError as error:
            callback(None, f"네이버 로그인 콜백 서버를 열지 못했습니다 ({error}). Blog Draft Agent를 한 번만 실행한 뒤 다시 시도해 주세요.")
            return

        def run() -> None:
            try:
                # Keep listening when the callback URL is opened manually without OAuth parameters.
                deadline = time.monotonic() + 180
                server.timeout = 1
                while time.monotonic() < deadline and not result.get("received"):
                    server.handle_request()
                if not result.get("received"):
                    raise RuntimeError("네이버 로그인 시간이 만료되었습니다. 앱의 ‘네이버 로그인’ 버튼에서 다시 시작해 주세요.")
                if result.get("error"):
                    description = result.get("error_description")
                    raise RuntimeError(f"네이버 로그인 오류: {result['error']}{f' ({description})' if description else ''}")
                if not result.get("code") or result.get("state") != state:
                    raise RuntimeError("네이버 로그인 상태 검증에 실패했습니다. 앱에서 로그인을 다시 시작해 주세요.")
                callback(self._fetch_profile(result["code"], state), None)
            except Exception as error:  # User-facing boundary for network and OAuth errors.
                callback(None, str(error))
            finally:
                server.server_close()

        # Bind the callback port before opening the browser. This prevents a fast redirect race.
        threading.Thread(target=run, daemon=True).start()
        query = urlencode(
            {
                "response_type": "code",
                "client_id": self.settings.naver_client_id,
                "redirect_uri": self.settings.naver_redirect_uri,
                "state": state,
            }
        )
        try:
            webbrowser.open(f"https://nid.naver.com/oauth2.0/authorize?{query}")
        except Exception as error:
            server.server_close()
            callback(None, f"네이버 로그인 브라우저를 열지 못했습니다: {error}")

    @staticmethod
    def _create_callback_server(host: str, port: int, callback_path: str) -> tuple[HTTPServer, dict[str, str | bool]]:
        result: dict[str, str | bool] = {"received": False}

        class CallbackServer(HTTPServer):
            allow_reuse_address = True

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802 - required by BaseHTTPRequestHandler
                request_path = urlparse(self.path)
                if request_path.path != callback_path:
                    self.send_error(404)
                    return
                values = parse_qs(request_path.query)
                code = values.get("code", [""])[0]
                error = values.get("error", [""])[0]
                if code or error:
                    result.update(
                        {
                            "received": True,
                            "code": code,
                            "state": values.get("state", [""])[0],
                            "error": error,
                            "error_description": values.get("error_description", [""])[0],
                        }
                    )
                    message = "<h2>로그인 확인이 완료되었습니다.</h2><p>이 창을 닫고 Blog Draft Agent로 돌아가세요.</p>"
                else:
                    message = "<h2>네이버 로그인 대기 중입니다.</h2><p>이 주소를 직접 열지 말고 Blog Draft Agent의 ‘네이버 로그인’ 버튼에서 시작해 주세요.</p>"
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(message.encode("utf-8"))

            def log_message(self, format, *args):  # noqa: A002
                return

        return CallbackServer((host, port), Handler), result

    def _fetch_profile(self, code: str, state: str) -> NaverProfile:
        token_query = urlencode(
            {
                "grant_type": "authorization_code",
                "client_id": self.settings.naver_client_id,
                "client_secret": self.settings.naver_client_secret,
                "code": code,
                "state": state,
            }
        )
        with urlopen(f"https://nid.naver.com/oauth2.0/token?{token_query}", timeout=30) as response:
            token_payload = json.loads(response.read().decode("utf-8"))
        access_token = token_payload.get("access_token")
        if not access_token:
            details = token_payload.get("error_description") or token_payload.get("error") or "알 수 없는 오류"
            raise RuntimeError(f"네이버 액세스 토큰을 받지 못했습니다: {details}")

        request = Request("https://openapi.naver.com/v1/nid/me", headers={"Authorization": f"Bearer {access_token}"})
        with urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
        profile = payload.get("response", {})
        return NaverProfile(nickname=profile.get("nickname") or "네이버 사용자", email=profile.get("email", ""))
