import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import main


class TopicExplainerTests(unittest.TestCase):
    def test_real_photos_are_the_default_visual_source(self):
        args = main.build_parser().parse_args(
            ["The 2001 financial crisis in Turkey", "--skip-cover"]
        )
        self.assertEqual(args.visual_source, "real")
        self.assertEqual(args.real_photo_min_match, 70)
        self.assertTrue(args.skip_cover)

    def test_existing_run_can_be_resumed_without_a_topic_argument(self):
        args = main.build_parser().parse_args(
            ["--resume-run", "outputs/previous-run", "--skip-cover"]
        )

        self.assertIsNone(args.topic)
        self.assertEqual(str(args.resume_run), "outputs/previous-run")

    def test_ass_overlays_offset_and_animate_captions(self):
        scene = main.ExplainerScene(
            date_label="SEPTEMBER 11, 2001",
            time_label="8:46 AM",
            location_label="NORTH TOWER, NEW YORK",
            retention_beat="Open the chronology.",
            narration="A concise factual narration begins here.",
            visual_anchor="An exact documentary photograph.",
            photo_requirement="Exact event photograph.",
            real_photo_queries=["exact event 2001", "event location 2001"],
            image_prompt="A detailed documentary frame.",
        )
        plan = main.ExplainerPlan(
            title="A Long Factual Documentary Timeline",
            character_bible="Verified historical context.",
            visual_style="Restrained documentary treatment.",
            scenes=[scene],
        )

        with tempfile.TemporaryDirectory() as temporary_directory:
            output_root = Path(temporary_directory)
            srt_path = output_root / "subtitles.srt"
            ass_path = output_root / "overlays.ass"
            main.write_subtitles(
                plan=plan,
                durations=[4.0],
                output_path=srt_path,
                start_offset=2.5,
            )
            main.write_ass_overlays(
                plan=plan,
                durations=[4.0],
                output_path=ass_path,
                start_offset=2.5,
            )
            srt = srt_path.read_text(encoding="utf-8")
            ass = ass_path.read_text(encoding="utf-8")

        self.assertIn("00:00:02,500 -->", srt)
        self.assertIn(r"\kf", ass)
        self.assertIn(r"SEPTEMBER 11, 2001 • 8:46 AM\NNORTH TOWER", ass)
        self.assertIn("A SHORT FACTUAL EXPLAINER", ass)

    @patch("main.genai.Client")
    def test_prompt_requires_authentic_topic_specific_evidence(self, client_class):
        response = {
            "title": "Turkey's 2001 Shock",
            "character_bible": "Turkey, Ankara, banks, and officials in 2001.",
            "visual_style": "Authentic archival documentary photography.",
            "scenes": [
                {
                    "retention_beat": "Open the central question.",
                    "narration": "In 2001, Turkey's lira suddenly lost value.",
                    "visual_anchor": "A Turkish lira banknote from the 2001 period.",
                    "photo_requirement": (
                        "A primary-source image of actual Turkish currency in 2001."
                    ),
                    "real_photo_queries": [
                        "Turkish lira banknote 2001",
                        "Türkiye banknot 2001",
                    ],
                    "image_prompt": "A period Turkish lira banknote in close view.",
                },
                {
                    "retention_beat": "Explain the political trigger.",
                    "narration": "A confrontation exposed deeper financial weakness.",
                    "visual_anchor": "Prime Minister Bülent Ecevit in Ankara in 2001.",
                    "photo_requirement": (
                        "The actual named prime minister in the correct year."
                    ),
                    "real_photo_queries": [
                        "Bülent Ecevit Ankara 2001",
                        "Bulent Ecevit 2001",
                    ],
                    "image_prompt": "Documentary image of Bülent Ecevit in Ankara.",
                },
            ],
        }
        create = Mock(
            return_value=SimpleNamespace(output_text=json.dumps(response))
        )
        client_class.return_value.interactions.create = create

        plan = main.generate_explainer(
            api_key="test",
            topic="The 2001 financial crisis in Turkey",
            language="English",
            target_seconds=20,
            scene_count=2,
            visual_source="real",
        )

        self.assertEqual(plan.scenes[1].real_photo_queries[0], "Bülent Ecevit Ankara 2001")
        prompt = create.call_args.kwargs["input"]
        self.assertIn("AUTHENTIC REAL-PHOTO METHOD", prompt)
        self.assertIn("actual topic—not generic stock", prompt)
        self.assertIn("Never label a related or representative photograph", prompt)
        self.assertIn("exact proper nouns", prompt)
        self.assertNotIn("NICHE PROFILE", prompt)


if __name__ == "__main__":
    unittest.main()
