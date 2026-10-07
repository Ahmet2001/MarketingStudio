import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from api_retry import RetryPolicy
from niche_profiles import load_niche_profile
from research import research_topic, save_research


class ResearchTests(unittest.TestCase):
    def test_research_can_run_without_a_niche_profile(self):
        client = Mock()
        client.text.return_value = []

        brief = research_topic(
            topic="A banking crisis",
            profile=None,
            max_results=1,
            scrape_pages=0,
            retry_policy=RetryPolicy(max_attempts=1),
            search_client=client,
        )

        self.assertEqual(brief.niche_id, "disabled")
        self.assertIn("essential context key details significance", brief.query)

    def test_no_results_query_moves_to_the_next_query_without_retrying(self):
        client = Mock()
        client.text.side_effect = [
            RuntimeError("No results found."),
            RuntimeError("No results found."),
            [
                {
                    "title": "Official report",
                    "href": "https://example.gov/report",
                    "body": "Verified timeline.",
                }
            ],
        ]

        with patch("api_retry.time.sleep") as sleep:
            brief = research_topic(
                topic="A financial collapse",
                profile=load_niche_profile("business-marketing"),
                queries=[
                    "first overly narrow query",
                    "financial collapse official report",
                ],
                research_focus="Verify the collapse timeline.",
                max_results=1,
                scrape_pages=0,
                retry_policy=RetryPolicy(max_attempts=6),
                search_client=client,
            )

        self.assertEqual(client.text.call_count, 3)
        sleep.assert_not_called()
        self.assertEqual(len(brief.sources), 1)
        self.assertEqual(
            brief.sources[0].search_query,
            "financial collapse official report",
        )
        self.assertEqual(brief.queries[0], "first overly narrow query")
        self.assertEqual(
            brief.research_focus,
            "Verify the collapse timeline.",
        )

    def test_automatic_backend_is_used_when_duckduckgo_has_no_results(self):
        client = Mock()
        client.text.side_effect = [
            RuntimeError("No results found."),
            [
                {
                    "title": "Fallback source",
                    "href": "https://example.com/fallback",
                    "body": "Fallback result.",
                }
            ],
        ]

        brief = research_topic(
            topic="A financial collapse",
            profile=load_niche_profile("business-marketing"),
            queries=["Barings Bank collapse official report"],
            max_results=1,
            scrape_pages=0,
            retry_policy=RetryPolicy(max_attempts=1),
            search_client=client,
        )

        backends = [
            call.kwargs["backend"] for call in client.text.call_args_list
        ]
        self.assertEqual(backends, ["duckduckgo", "auto"])
        self.assertEqual(brief.sources[0].search_backend, "auto")
        self.assertEqual(brief.search_backends, ["duckduckgo", "auto"])

    def test_duckduckgo_results_are_extracted_and_deduplicated(self):
        client = Mock()
        client.text.return_value = [
            {
                "title": "First source",
                "href": "https://example.com/first",
                "body": "First snippet.",
            },
            {
                "title": "Duplicate",
                "href": "https://example.com/first",
                "body": "Duplicate snippet.",
            },
            {
                "title": "Second source",
                "href": "https://example.org/second",
                "body": "Second snippet.",
            },
        ]
        client.extract.return_value = {
            "content": "Extracted page text with useful factual context."
        }
        profile = load_niche_profile("history")

        brief = research_topic(
            topic="An ancient road",
            profile=profile,
            max_results=3,
            scrape_pages=1,
            retry_policy=RetryPolicy(max_attempts=1),
            search_client=client,
        )

        self.assertEqual(len(brief.sources), 2)
        self.assertEqual(
            brief.sources[0].extracted_text,
            "Extracted page text with useful factual context.",
        )
        self.assertEqual(brief.sources[1].extracted_text, "")
        self.assertEqual(client.text.call_args.kwargs["backend"], "duckduckgo")
        self.assertEqual(brief.sources[0].search_backend, "duckduckgo")
        client.extract.assert_called_once_with(
            "https://example.com/first", fmt="text_plain"
        )

    def test_search_network_failure_is_retried(self):
        client = Mock()
        client.text.side_effect = [
            ConnectionError("temporary connection failure"),
            [
                {
                    "title": "Recovered source",
                    "href": "https://example.com/recovered",
                    "body": "Recovered.",
                }
            ],
        ]

        with patch("api_retry.time.sleep"):
            brief = research_topic(
                topic="A topic",
                profile=load_niche_profile("science"),
                max_results=1,
                scrape_pages=0,
                retry_policy=RetryPolicy(
                    max_attempts=2,
                    base_delay=0,
                    max_delay=0,
                ),
                search_client=client,
            )

        self.assertEqual(client.text.call_count, 2)
        self.assertEqual(brief.sources[0].title, "Recovered source")

    def test_failed_extraction_falls_back_to_search_snippet(self):
        client = Mock()
        client.text.return_value = [
            {
                "title": "Snippet source",
                "href": "https://example.com/snippet",
                "body": "Usable search snippet.",
            }
        ]
        client.extract.side_effect = TimeoutError("timed out")

        brief = research_topic(
            topic="A topic",
            profile=load_niche_profile("travel"),
            max_results=1,
            scrape_pages=1,
            retry_policy=RetryPolicy(max_attempts=1),
            search_client=client,
        )

        self.assertEqual(brief.sources[0].extracted_text, "")
        self.assertIn("Usable search snippet.", brief.to_prompt())

    def test_forbidden_extraction_is_not_retried(self):
        client = Mock()
        client.text.return_value = [
            {
                "title": "Blocked source",
                "href": "https://example.com/blocked",
                "body": "The search result still provides a useful snippet.",
            }
        ]
        client.extract.side_effect = RuntimeError(
            "Failed to fetch https://example.com/blocked: HTTP 403"
        )

        with patch("api_retry.time.sleep") as sleep:
            brief = research_topic(
                topic="A topic",
                profile=load_niche_profile("science"),
                max_results=1,
                scrape_pages=1,
                retry_policy=RetryPolicy(max_attempts=6),
                search_client=client,
            )

        client.extract.assert_called_once()
        sleep.assert_not_called()
        self.assertEqual(brief.sources[0].extracted_text, "")
        self.assertIn("useful snippet", brief.to_prompt())

    def test_research_brief_can_be_saved(self):
        client = Mock()
        client.text.return_value = []
        brief = research_topic(
            topic="A topic",
            profile=load_niche_profile(),
            max_results=1,
            scrape_pages=0,
            retry_policy=RetryPolicy(max_attempts=1),
            search_client=client,
        )

        with tempfile.TemporaryDirectory() as temporary_directory:
            output_path = Path(temporary_directory) / "research.json"
            save_research(brief, output_path)
            saved = output_path.read_text(encoding="utf-8")

        self.assertIn('"niche_id": "general-storytelling"', saved)


if __name__ == "__main__":
    unittest.main()
