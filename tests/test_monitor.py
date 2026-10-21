"""Проверка сравнения снимков без сети и без ключа API."""

import unittest

from backend.services.monitor_service import content_hash, diff_snapshots
from backend.services.openaiservice import clamp_score, competitor_from_json, image_from_json
from backend.services.parsingservice import parsing_service


class ScoreTests(unittest.TestCase):
    def test_clamp(self):
        self.assertEqual(clamp_score(8), 8)
        self.assertEqual(clamp_score("11"), 10)
        self.assertEqual(clamp_score(-3), 0)
        self.assertEqual(clamp_score("высокий"), 0)

    def test_competitor_fields(self):
        analysis = competitor_from_json(
            {
                "summary": "Сильный лендинг",
                "design_score": 9,
                "animation_potential": 8,
                "animation_notes": "Есть интерактивный риг",
                "strengths": ["демо в герое"],
            }
        )
        self.assertEqual(analysis.design_score, 9)
        self.assertEqual(analysis.animation_potential, 8)
        self.assertIn("9/10", analysis.conclusion)

    def test_image_fields(self):
        analysis = image_from_json({"description": "Герой", "visual_style_score": 6, "animation_potential": 4})
        self.assertEqual(analysis.design_score, 6)
        self.assertEqual(analysis.animation_potential, 4)


class DiffTests(unittest.TestCase):
    def test_same_page_has_no_changes(self):
        digest = content_hash("Rive", "Animate", "Build interactive motion")
        previous = {
            "title": "Rive",
            "h1": "Animate",
            "text_excerpt": "Build interactive motion",
            "content_hash": digest,
            "analysis": {"design_score": 8, "animation_potential": 9, "summary": "Лидер"},
        }
        current = dict(previous)
        current["analysis"] = dict(previous["analysis"], summary="Другая формулировка модели")
        self.assertEqual(diff_snapshots(previous, current), [])

    def test_headline_change_is_recorded(self):
        previous = {
            "title": "Старый",
            "h1": "Было",
            "text_excerpt": "текст один",
            "content_hash": "a",
            "analysis": {"design_score": 5, "animation_potential": 5, "summary": "ровно"},
        }
        current = {
            "title": "Новый",
            "h1": "Стало",
            "text_excerpt": "текст два",
            "content_hash": "b",
            "analysis": {"design_score": 8, "animation_potential": 5, "summary": "сильнее"},
        }
        fields = [item["field"] for item in diff_snapshots(previous, current)]
        self.assertIn("Заголовок", fields)
        self.assertIn("Оценка дизайна", fields)
        self.assertNotIn("Потенциал анимации", fields)

    def test_url_normalization(self):
        self.assertEqual(parsing_service.normalize_url("rive.app"), "https://rive.app")


if __name__ == "__main__":
    unittest.main()
