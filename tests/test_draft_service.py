import unittest

from blog_agent.config import Settings
from blog_agent.draft_service import generate_body, generate_outline


class DraftWorkflowTests(unittest.TestCase):
    def test_local_mode_creates_outline_then_body_without_an_api_key(self):
        settings = Settings()
        outline = generate_outline(
            settings,
            "서해구 순대국 방문",
            "점심에 방문했고 얼큰순대국을 먹었다.",
            [],
            [],
            "안녕하세요, 오늘은 맛집을 소개해 드리려 합니다.",
            "맛집 후기",
        )
        body = generate_body(
            settings,
            "서해구 순대국 방문",
            "점심에 방문했고 얼큰순대국을 먹었다.",
            [],
            [],
            "안녕하세요, 오늘은 맛집을 소개해 드리려 합니다.",
            "맛집 후기",
            outline.content,
            outline.image_analysis,
        )

        self.assertFalse(outline.used_remote_model)
        self.assertIn("# 글 구성", outline.content)
        self.assertIn("## 방문하게 된 계기", body.content)


if __name__ == "__main__":
    unittest.main()
