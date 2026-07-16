import threading
import unittest
from urllib.request import urlopen

from blog_agent.config import Settings
from blog_agent.naver_oauth import NaverLogin


class NaverOAuthTests(unittest.TestCase):
    def test_missing_credentials_returns_a_clear_error(self):
        received = []
        NaverLogin(Settings()).start(lambda profile, error: received.append((profile, error)))

        self.assertEqual(received[0][0], None)
        self.assertIn("Client ID", received[0][1])

    def test_plain_callback_does_not_complete_the_oauth_attempt(self):
        server, result = NaverLogin._create_callback_server("127.0.0.1", 0, "/callback")
        port = server.server_address[1]
        try:
            worker = threading.Thread(target=server.handle_request)
            worker.start()
            with urlopen(f"http://127.0.0.1:{port}/callback", timeout=3) as response:
                self.assertEqual(response.status, 200)
            worker.join(timeout=3)
            self.assertFalse(result["received"])
        finally:
            server.server_close()


if __name__ == "__main__":
    unittest.main()
