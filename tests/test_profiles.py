import tempfile
import unittest
from pathlib import Path

from blog_agent.profiles import ThemeProfileStore


class ThemeProfileStoreTests(unittest.TestCase):
    def test_saved_samples_are_loaded_for_the_same_theme(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ThemeProfileStore(Path(directory) / "profiles.json")
            store.save("맛집 후기", "안녕하세요, 오늘은 맛집을 소개해 드리려 합니다.")

            self.assertEqual(
                store.load("맛집 후기"),
                "안녕하세요, 오늘은 맛집을 소개해 드리려 합니다.",
            )
            self.assertEqual(store.load("여행"), "")


if __name__ == "__main__":
    unittest.main()
