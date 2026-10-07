import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from urllib.error import URLError
from unittest.mock import Mock, patch

from api_retry import RetryPolicy
from real_photos import (
    RealPhotoCandidate,
    OpenverseClient,
    WikimediaCommonsClient,
    _query_variants,
    download_scene_real_photos,
    save_real_photo_credits,
    save_real_photo_manifest,
)


class _FakeResponse:
    def __init__(self, body: bytes, content_type: str = "application/json"):
        self.body = body
        self.headers = {"Content-Type": content_type}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self):
        return self.body


def _candidate(page_id: int, title: str) -> RealPhotoCandidate:
    return RealPhotoCandidate(
        search_query="Bulent Ecevit 2001 Turkey",
        page_id=page_id,
        title=title,
        page_url=f"https://commons.wikimedia.org/wiki/File:{page_id}.jpg",
        image_url=(
            f"https://upload.wikimedia.org/wikipedia/commons/thumb/a/ab/"
            f"{page_id}.jpg/1600px-{page_id}.jpg"
        ),
        preview_url=(
            f"https://upload.wikimedia.org/wikipedia/commons/thumb/a/ab/"
            f"{page_id}.jpg/1600px-{page_id}.jpg"
        ),
        mime_type="image/jpeg",
        width=1600,
        height=1000,
        creator="Documentary Photographer",
        credit="National archive",
        license="CC BY-SA 4.0",
        license_url="https://creativecommons.org/licenses/by-sa/4.0/",
        usage_terms="Creative Commons Attribution-ShareAlike 4.0",
        date_created="2001-02-20",
        description="Bülent Ecevit speaking in Ankara in 2001.",
        categories="Photographs of Bülent Ecevit",
    )


class WikimediaCommonsClientTests(unittest.TestCase):
    def test_over_specific_queries_are_relaxed_around_the_named_subject(self):
        variants = _query_variants("Istanbul Stock Exchange building 2001")

        self.assertEqual(
            variants,
            [
                "Istanbul Stock Exchange building",
                "Istanbul Stock Exchange",
            ],
        )
        self.assertIn(
            "Ziraat Bank Ankara",
            _query_variants("TC Ziraat Bankasi Ankara 1999"),
        )

    def test_openverse_returns_commercially_reusable_photographs(self):
        payload = {
            "results": [
                {
                    "id": "75222bb3-7fa7-4fa5-8c0c-2849c1cceae7",
                    "title": "Ziraat Bank Building at Ankara",
                    "creator": "Archive Photographer",
                    "creator_url": "https://www.flickr.com/photos/archive",
                    "license": "by-sa",
                    "license_version": "2.0",
                    "license_url": (
                        "https://creativecommons.org/licenses/by-sa/2.0/"
                    ),
                    "source": "flickr",
                    "url": (
                        "https://live.staticflickr.com/3151/"
                        "2899096106_1fcc520665_b.jpg"
                    ),
                    "thumbnail": (
                        "https://api.openverse.org/v1/images/"
                        "75222bb3-7fa7-4fa5-8c0c-2849c1cceae7/thumb/"
                    ),
                    "foreign_landing_url": (
                        "https://www.flickr.com/photos/archive/2899096106"
                    ),
                    "width": 1024,
                    "height": 632,
                    "tags": [{"name": "Ankara"}, {"name": "Ziraat Bank"}],
                }
            ]
        }
        opener = Mock(
            return_value=_FakeResponse(json.dumps(payload).encode())
        )
        client = OpenverseClient(
            retry_policy=RetryPolicy(max_attempts=1),
            opener=opener,
            user_agent="TopicExplainerTests/1.0",
            minimum_search_interval=0,
        )

        candidates = client.search("Ziraat Bank Ankara", per_page=8)

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].provider, "Openverse (flickr)")
        self.assertEqual(candidates[0].license, "BY-SA 2.0")
        request = opener.call_args.args[0]
        self.assertIn("categories=photograph", request.full_url)
        self.assertIn("license=by%2Cby-sa%2Ccc0%2Cpdm", request.full_url)

    def test_search_retries_and_filters_synthetic_or_non_photo_results(self):
        payload = {
            "query": {
                "pages": [
                    {
                        "pageid": 11,
                        "title": "File:Ecevit Ankara 2001.jpg",
                        "imageinfo": [
                            {
                                "thumburl": (
                                    "https://upload.wikimedia.org/wikipedia/"
                                    "commons/thumb/a/ab/ecevit.jpg/1600px-ecevit.jpg"
                                ),
                                "mime": "image/jpeg",
                                "mediatype": "BITMAP",
                                "width": 2400,
                                "height": 1600,
                                "extmetadata": {
                                    "Artist": {"value": "Archive Photographer"},
                                    "ImageDescription": {
                                        "value": "<b>Bülent Ecevit</b> in Ankara."
                                    },
                                    "LicenseShortName": {
                                        "value": "CC BY-SA 4.0"
                                    },
                                    "LicenseUrl": {
                                        "value": (
                                            "https://creativecommons.org/"
                                            "licenses/by-sa/4.0/"
                                        )
                                    },
                                    "Categories": {
                                        "value": "Photographs of Bülent Ecevit"
                                    },
                                },
                            }
                        ],
                    },
                    {
                        "pageid": 22,
                        "title": "File:AI-generated crisis scene.png",
                        "imageinfo": [
                            {
                                "thumburl": (
                                    "https://upload.wikimedia.org/wikipedia/"
                                    "commons/thumb/c/cd/fake.png/1600px-fake.png"
                                ),
                                "mime": "image/png",
                                "mediatype": "BITMAP",
                                "width": 1200,
                                "height": 1800,
                                "extmetadata": {
                                    "ImageDescription": {
                                        "value": "AI-generated illustration"
                                    },
                                    "LicenseShortName": {"value": "CC0"},
                                },
                            }
                        ],
                    },
                ]
            }
        }
        opener = Mock(
            side_effect=[
                URLError("temporary"),
                _FakeResponse(json.dumps(payload).encode()),
            ]
        )
        client = WikimediaCommonsClient(
            retry_policy=RetryPolicy(
                max_attempts=2,
                base_delay=0,
                max_delay=0,
            ),
            opener=opener,
            user_agent="TopicExplainerTests/1.0 (tests@example.com)",
            minimum_search_interval=0,
        )

        with patch("api_retry.time.sleep"):
            candidates = client.search(
                "Bülent Ecevit Ankara 2001",
                per_page=8,
            )

        self.assertEqual([candidate.page_id for candidate in candidates], [11])
        request = opener.call_args.args[0]
        self.assertIn("gsrnamespace=6", request.full_url)
        self.assertIn("filetype%3Abitmap", request.full_url)
        self.assertIn("iiurlwidth=1600", request.full_url)
        self.assertEqual(
            request.get_header("User-agent"),
            "TopicExplainerTests/1.0 (tests@example.com)",
        )


class RealPhotoPipelineTests(unittest.TestCase):
    def test_scene_search_never_borrows_another_scenes_queries(self):
        unrelated = _candidate(909, "File:Unrelated-scene.jpg")
        client = Mock()
        client.search.side_effect = (
            lambda query, per_page: (
                [unrelated] if query.startswith("Scene Two Subject") else []
            )
        )

        with tempfile.TemporaryDirectory() as temporary_directory:
            with self.assertRaisesRegex(
                RuntimeError,
                "no usable authentic photo for scene 1",
            ):
                download_scene_real_photos(
                    client=client,
                    scene_queries=[
                        ["Scene One Exact Event 2001"],
                        ["Scene Two Subject 2001"],
                    ],
                    images_dir=Path(temporary_directory),
                    per_query=8,
                    max_candidates=4,
                )

        searched_queries = [
            call.args[0] for call in client.search.call_args_list
        ]
        self.assertFalse(
            any(query.startswith("Scene Two Subject") for query in searched_queries)
        )

    def test_empty_exact_queries_fall_back_to_broader_named_subject(self):
        exchange = _candidate(303, "File:Istanbul-stock.jpg")
        client = Mock()
        client.search.side_effect = (
            lambda query, per_page: (
                [exchange] if query == "Istanbul Stock Exchange" else []
            )
        )
        client.download.return_value = b"exchange-photo"

        with tempfile.TemporaryDirectory() as temporary_directory:
            image_paths, manifest = download_scene_real_photos(
                client=client,
                scene_queries=[
                    [
                        "Istanbul Stock Exchange building 2001",
                        "İMKB 2001 kriz",
                        "Turkey stock market crash 2001",
                    ]
                ],
                scene_narrations=["Turkish markets suffered record losses."],
                visual_anchors=["The actual Istanbul exchange building."],
                photo_requirements=["Actual institution or period context."],
                images_dir=Path(temporary_directory),
                per_query=8,
                max_candidates=1,
            )
            downloaded = image_paths[0].read_bytes()

        searched_queries = [
            call.args[0] for call in client.search.call_args_list
        ]
        self.assertIn("Istanbul Stock Exchange", searched_queries)
        self.assertEqual(manifest.photos[0].page_id, 303)
        self.assertEqual(downloaded, b"exchange-photo")

    def test_queries_are_combined_duplicates_are_avoided_and_credits_are_saved(self):
        first = _candidate(101, "File:Ecevit 2001.jpg")
        second = _candidate(202, "File:Turkish lira 2001.jpg")
        client = Mock()
        client.search.side_effect = [
            [first],
            [first],
            [first, second],
            [second],
        ]
        client.download.side_effect = [b"first-photo", b"second-photo"]

        def select(
            scene_number,
            narration,
            visual_anchor,
            photo_requirement,
            candidates,
        ):
            self.assertTrue(narration)
            self.assertTrue(visual_anchor)
            self.assertIn("actual", photo_requirement)
            return replace(
                candidates[0],
                match_score=88,
                match_reason="Correct named subject and year.",
                depiction_type="actual_subject",
            )

        with tempfile.TemporaryDirectory() as temporary_directory:
            output_root = Path(temporary_directory)
            images_dir = output_root / "images"
            images_dir.mkdir()
            image_paths, manifest = download_scene_real_photos(
                client=client,
                scene_queries=[
                    ["Bülent Ecevit 2001", "Ecevit Ankara"],
                    ["Turkish lira 2001", "Turkey banknotes 2001"],
                ],
                scene_narrations=["The political break became visible.", "The lira fell."],
                visual_anchors=["Ecevit in Ankara.", "A period Turkish lira note."],
                photo_requirements=[
                    "The actual prime minister in 2001.",
                    "The actual currency from the period.",
                ],
                candidate_selector=select,
                images_dir=images_dir,
                per_query=10,
                max_candidates=1,
            )
            manifest_path = output_root / "real_photos.json"
            credits_path = output_root / "real_photo_credits.txt"
            save_real_photo_manifest(manifest, manifest_path)
            save_real_photo_credits(manifest, credits_path)
            saved = json.loads(manifest_path.read_text(encoding="utf-8"))
            credits = credits_path.read_text(encoding="utf-8")
            first_photo_bytes = image_paths[0].read_bytes()

        self.assertEqual(first_photo_bytes, b"first-photo")
        self.assertEqual(
            [photo.page_id for photo in manifest.photos],
            [101, 202],
        )
        self.assertEqual(saved["photos"][0]["depiction_type"], "actual_subject")
        self.assertIn("CC BY-SA 4.0", credits)
        self.assertIn("Scene 2", credits)


if __name__ == "__main__":
    unittest.main()
