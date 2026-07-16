import unittest

from blog_agent.style import build_style_profile, choose_reference_samples


class StyleProfileTests(unittest.TestCase):
    def test_empty_samples_produce_a_safe_default(self):
        self.assertIn("친절한", build_style_profile(""))

    def test_topic_related_block_is_selected_first(self):
        samples = "카페 방문 기록입니다.\n\n등산을 다녀온 날의 기록입니다."
        result = choose_reference_samples(samples, "등산 후기")
        self.assertIn("등산", result[0])


if __name__ == "__main__":
    unittest.main()
