import unittest

from blog_agent.style import build_style_profile, choose_reference_samples, theme_guide


class StyleProfileTests(unittest.TestCase):
    def test_empty_samples_produce_a_safe_default(self):
        profile = build_style_profile("", "맛집 후기")
        self.assertIn("테마: 맛집 후기", profile)
        self.assertIn("샘플 글이 없으므로", profile)

    def test_restaurant_theme_has_a_review_structure(self):
        guide = theme_guide("맛집 후기")
        self.assertIn("메뉴/가격", guide)
        self.assertIn("방문 후기", guide)

    def test_topic_related_block_is_selected_first(self):
        samples = "카페 방문 기록입니다.\n\n등산을 다녀온 날의 기록입니다."
        result = choose_reference_samples(samples, "등산 후기")
        self.assertIn("등산", result[0])


if __name__ == "__main__":
    unittest.main()
