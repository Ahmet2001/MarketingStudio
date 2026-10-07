import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from api_retry import RetryPolicy
from photo_ranker import GeminiRealPhotoRanker
from real_photos import RealPhotoCandidate


def _candidate(page_id: int, title: str) -> RealPhotoCandidate:
    return RealPhotoCandidate(
        search_query="Turkey crisis 2001",
        page_id=page_id,
        title=title,
        page_url=f"https://commons.wikimedia.org/wiki/File:{page_id}.jpg",
        image_url=f"https://upload.wikimedia.org/{page_id}.jpg",
        preview_url=f"https://upload.wikimedia.org/{page_id}.jpg",
        mime_type="image/jpeg",
        width=1200,
        height=900,
        creator="Photographer",
        credit="Archive",
        license="Public domain",
        license_url="",
        usage_terms="Public domain",
        date_created="2001",
        description=title,
        categories="Documentary photographs",
    )


class GeminiRealPhotoRankerTests(unittest.TestCase):
    @patch("photo_ranker.genai.Client")
    def test_ranker_preserves_honest_depiction_type(self, client_class):
        response = {
            "candidate_number": 2,
            "match_score": 91,
            "depiction_type": "exact_event",
            "authenticity_confirmed": True,
            "requirement_satisfied": True,
            "reason": "The metadata and image show the named 2001 event.",
        }
        generate_content = Mock(
            return_value=SimpleNamespace(text=json.dumps(response))
        )
        client_class.return_value.models.generate_content = generate_content
        commons_client = Mock()
        commons_client.download.return_value = b"jpeg"

        ranker = GeminiRealPhotoRanker(
            api_key="test",
            model="test-model",
            retry_policy=RetryPolicy(max_attempts=1),
            minimum_match_score=60,
        )
        selected = ranker.select(
            scene_number=1,
            narration="Turkey entered a severe financial crisis in 2001.",
            visual_anchor="An authentic photograph from the crisis.",
            photo_requirement="Exact-event evidence from Turkey in 2001.",
            candidates=[
                _candidate(1, "Generic Ankara crowd"),
                _candidate(2, "Turkey financial crisis 2001"),
            ],
            commons_client=commons_client,
        )

        self.assertEqual(selected.page_id, 2)
        self.assertEqual(selected.match_score, 91)
        self.assertEqual(selected.depiction_type, "exact_event")
        prompt = generate_content.call_args.kwargs["contents"][0]
        self.assertIn("Reject staged stock imagery", prompt)
        self.assertIn("Use depiction_type `exact_event` only", prompt)

    @patch("photo_ranker.genai.Client")
    def test_ranker_rejects_weak_generic_match(self, client_class):
        client_class.return_value.models.generate_content.return_value = (
            SimpleNamespace(
                text=json.dumps(
                    {
                        "candidate_number": 1,
                        "match_score": 42,
                        "depiction_type": "period_context",
                        "authenticity_confirmed": True,
                        "requirement_satisfied": False,
                        "reason": "Generic office image with uncertain date.",
                    }
                )
            )
        )
        commons_client = Mock()
        commons_client.download.return_value = b"jpeg"
        ranker = GeminiRealPhotoRanker(
            api_key="test",
            model="test-model",
            retry_policy=RetryPolicy(max_attempts=1),
            minimum_match_score=60,
        )

        with self.assertRaisesRegex(RuntimeError, "No sufficiently relevant"):
            ranker.select(
                scene_number=1,
                narration="A currency crisis unfolded.",
                visual_anchor="Actual Turkish crisis evidence.",
                photo_requirement="Actual event or primary source.",
                candidates=[_candidate(1, "Office worker")],
                commons_client=commons_client,
            )

    @patch("photo_ranker.genai.Client")
    def test_exact_event_requirement_rejects_period_context(self, client_class):
        client_class.return_value.models.generate_content.return_value = (
            SimpleNamespace(
                text=json.dumps(
                    {
                        "candidate_number": 1,
                        "match_score": 95,
                        "depiction_type": "period_context",
                        "authenticity_confirmed": True,
                        "requirement_satisfied": True,
                        "reason": (
                            "Authentic related location, but it does not show "
                            "the exact event."
                        ),
                    }
                )
            )
        )
        commons_client = Mock()
        commons_client.download.return_value = b"jpeg"
        ranker = GeminiRealPhotoRanker(
            api_key="test",
            model="test-model",
            retry_policy=RetryPolicy(max_attempts=1),
            minimum_match_score=70,
        )

        with self.assertRaisesRegex(
            RuntimeError,
            "exact-event photograph was required",
        ):
            ranker.select(
                scene_number=1,
                narration="The exact event occurred.",
                visual_anchor="The event itself.",
                photo_requirement="Exact event photograph at the date and place.",
                candidates=[_candidate(1, "Related location")],
                commons_client=commons_client,
            )


if __name__ == "__main__":
    unittest.main()
