import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from replicate.exceptions import ReplicateError

import main
from api_retry import (
    RetryPolicy,
    api_status_code,
    call_with_retry,
    is_retryable_api_error,
    retry_after_seconds,
)


class RetryHelperTests(unittest.TestCase):
    def test_replicate_rate_limit_uses_reset_hint(self):
        operation = Mock(
            side_effect=[
                ReplicateError(
                    status=429,
                    detail="Rate limit resets in ~1s.",
                ),
                "success",
            ]
        )

        with patch("api_retry.time.sleep") as sleep:
            result = call_with_retry(
                operation,
                label="Replicate test",
                policy=RetryPolicy(max_attempts=3),
            )

        self.assertEqual(result, "success")
        self.assertEqual(operation.call_count, 2)
        sleep.assert_called_once_with(1.25)

    def test_authentication_error_is_not_retried(self):
        error = ReplicateError(status=401, detail="Invalid token")
        operation = Mock(side_effect=error)

        with patch("api_retry.time.sleep") as sleep:
            with self.assertRaises(ReplicateError):
                call_with_retry(
                    operation,
                    label="Replicate test",
                    policy=RetryPolicy(max_attempts=6),
                )

        self.assertEqual(operation.call_count, 1)
        sleep.assert_not_called()

    def test_network_failures_use_bounded_exponential_backoff(self):
        operation = Mock(
            side_effect=[
                ConnectionError("connection reset"),
                TimeoutError("timed out"),
                "success",
            ]
        )

        with (
            patch("api_retry.time.sleep") as sleep,
            patch("api_retry.random.random", return_value=0),
        ):
            result = call_with_retry(
                operation,
                label="Network test",
                policy=RetryPolicy(
                    max_attempts=3,
                    base_delay=2,
                    max_delay=3,
                ),
            )

        self.assertEqual(result, "success")
        self.assertEqual([call.args[0] for call in sleep.call_args_list], [2, 3])

    def test_status_and_retry_hint_helpers(self):
        error = ReplicateError(
            status=503,
            detail="Service unavailable. Retry after 500ms.",
        )
        self.assertEqual(api_status_code(error), 503)
        self.assertTrue(is_retryable_api_error(error))
        self.assertEqual(retry_after_seconds(error), 0.5)


class APIIntegrationRetryTests(unittest.TestCase):
    @patch("main.genai.Client")
    def test_gemini_story_call_retries_429(self, client_class):
        interaction = SimpleNamespace(
            output_text=(
                '{"title":"Test","character_bible":"Person","visual_style":"Film",'
                '"scenes":[{"retention_beat":"Hook.","narration":"One.",'
                '"visual_anchor":"A person sees one event.",'
                '"stock_queries":["person watching event","surprised observer"],'
                '"image_prompt":"One image."},'
                '{"retention_beat":"Payoff.","narration":"Two.",'
                '"visual_anchor":"A person sees the second event.",'
                '"stock_queries":["person observing event","person watching"],'
                '"image_prompt":"Two image."}]}'
            )
        )
        create = Mock(side_effect=[
            _StatusError(429, "resource exhausted"),
            interaction,
        ])
        client_class.return_value.interactions.create = create

        with patch("api_retry.time.sleep"):
            plan = main.generate_story(
                api_key="test",
                topic="test",
                language="English",
                target_seconds=20,
                scene_count=2,
                retry_policy=RetryPolicy(
                    max_attempts=2,
                    base_delay=0,
                    max_delay=0,
                ),
            )

        self.assertEqual(plan.title, "Test")
        self.assertEqual(create.call_count, 2)

    def test_replicate_image_call_retries_429_before_writing(self):
        file_output = Mock()
        file_output.read.return_value = b"image-bytes"
        client = Mock()
        client.run.side_effect = [
            ReplicateError(status=429, detail="Rate limit resets in ~0s."),
            file_output,
        ]

        with tempfile.TemporaryDirectory() as temporary_directory:
            output_path = Path(temporary_directory) / "image.png"
            with patch("api_retry.time.sleep"):
                main.generate_image(
                    client=client,
                    model="test/model",
                    prompt="test prompt",
                    output_path=output_path,
                    seed=None,
                    retry_policy=RetryPolicy(
                        max_attempts=2,
                        base_delay=0,
                        max_delay=0,
                    ),
                )
            self.assertEqual(output_path.read_bytes(), b"image-bytes")

        self.assertEqual(client.run.call_count, 2)

    def test_elevenlabs_stream_retry_discards_partial_audio(self):
        def interrupted_audio():
            yield b"partial-"
            raise ConnectionError("connection reset")

        client = Mock()
        client.text_to_speech.convert.side_effect = [
            interrupted_audio(),
            iter([b"complete-audio"]),
        ]

        with tempfile.TemporaryDirectory() as temporary_directory:
            output_path = Path(temporary_directory) / "audio.mp3"
            with patch("api_retry.time.sleep"):
                main.generate_tts(
                    client=client,
                    text="test",
                    output_path=output_path,
                    voice_id="voice",
                    model_id="model",
                    retry_policy=RetryPolicy(
                        max_attempts=2,
                        base_delay=0,
                        max_delay=0,
                    ),
                )
            self.assertEqual(output_path.read_bytes(), b"complete-audio")

        self.assertEqual(client.text_to_speech.convert.call_count, 2)


class _StatusError(Exception):
    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code


if __name__ == "__main__":
    unittest.main()
