import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import main
from niche_profiles import load_niche_profile
from research import ResearchBrief, ResearchSource


class StoryGenerationTests(unittest.TestCase):
    @patch("main.genai.Client")
    def test_research_planner_without_niche_is_topic_adaptive(
        self,
        client_class,
    ):
        response = {
            "research_focus": "Explain how coral polyps feed after sunset.",
            "queries": [
                "coral polyp nocturnal feeding behavior",
                "reef ecology after sunset",
                "coral night feeding scientific study",
            ],
        }
        create = Mock(
            return_value=SimpleNamespace(output_text=json.dumps(response))
        )
        client_class.return_value.interactions.create = create

        main.plan_research_queries(
            api_key="test-key",
            topic="How a coral reef changes after sunset",
            niche_profile=None,
        )

        prompt = create.call_args.kwargs["input"]
        self.assertIn("topic-appropriate research angles", prompt)
        self.assertIn("works, species, materials", prompt)
        self.assertIn("For fictional briefs", prompt)
        self.assertNotIn("underlying causes or mechanism", prompt)
        self.assertNotIn("verified timeline, mechanism or cause", prompt)

    @patch("main.genai.Client")
    def test_gemini_selects_concise_research_queries(self, client_class):
        response = {
            "research_focus": (
                "Verify how unauthorized trading and control failures caused "
                "Barings Bank to collapse."
            ),
            "queries": [
                "  Barings Bank collapse 1995 official report  ",
                "Nick Leeson unauthorized derivatives losses",
                "Barings Bank internal controls failure",
            ],
        }
        create = Mock(
            return_value=SimpleNamespace(output_text=json.dumps(response))
        )
        client_class.return_value.interactions.create = create

        plan = main.plan_research_queries(
            api_key="test-key",
            topic="Tell the verified story of the Barings Bank collapse.",
            niche_profile=load_niche_profile("business-marketing"),
        )

        self.assertEqual(
            plan.queries[0],
            "Barings Bank collapse 1995 official report",
        )
        self.assertEqual(len(plan.queries), 3)
        prompt = create.call_args.kwargs["input"]
        self.assertIn("Choose the central factual research focus yourself", prompt)
        self.assertIn("Do not copy the entire story brief", prompt)
        self.assertIn("primary sources", prompt)

    @patch("main.genai.Client")
    def test_duration_is_converted_to_a_tight_word_target(self, client_class):
        response = {
            "title": "Test Story",
            "character_bible": "A fictional traveler in a red coat.",
            "visual_style": "Cinematic night photography.",
            "scenes": [
                {
                    "retention_beat": "Hook — reveal the immediate danger.",
                    "narration": "A short line.",
                    "visual_anchor": "A traveler stops on a dark road.",
                    "stock_queries": [
                        "traveler dark empty road",
                        "person standing rural road",
                    ],
                    "image_prompt": "A traveler standing on a dark road.",
                },
                {
                    "retention_beat": "Payoff — show that the danger has passed.",
                    "narration": "The final line.",
                    "visual_anchor": "The traveler watches the sunrise.",
                    "stock_queries": [
                        "traveler watching sunrise",
                        "person sunrise silhouette",
                    ],
                    "image_prompt": "A traveler watching a sunrise.",
                },
            ],
        }
        create = Mock(
            return_value=SimpleNamespace(output_text=json.dumps(response))
        )
        client_class.return_value.interactions.create = create

        main.generate_story(
            api_key="test-key",
            topic="A test",
            language="English",
            target_seconds=20,
            scene_count=2,
        )

        prompt = create.call_args.kwargs["input"]
        self.assertIn("Aim for 56 spoken words total.", prompt)
        self.assertIn("between 53 and 59 words", prompt)
        self.assertIn("90–140 words", prompt)
        self.assertIn("foreground, midground, and background", prompt)
        self.assertIn("Vary shot sizes and camera angles", prompt)

    @patch("main.genai.Client")
    def test_story_prompt_and_word_target_follow_speaking_style(
        self,
        client_class,
    ):
        response = {
            "title": "Test Story",
            "character_bible": "A consistent setting.",
            "visual_style": "Cinematic.",
            "scenes": [
                {
                    "retention_beat": "Hook.",
                    "narration": "A quiet beginning.",
                    "visual_anchor": "A person waits.",
                    "image_prompt": "A person waits in a quiet room.",
                },
                {
                    "retention_beat": "Payoff.",
                    "narration": "The truth appears.",
                    "visual_anchor": "A hidden object is revealed.",
                    "image_prompt": "A hidden object appears in the room.",
                },
            ],
        }
        create = Mock(
            return_value=SimpleNamespace(output_text=json.dumps(response))
        )
        client_class.return_value.interactions.create = create

        main.generate_story(
            api_key="test-key",
            topic="A test",
            language="English",
            target_seconds=20,
            scene_count=2,
            speaking_style="sad",
            speech_speed=0.82,
            character_style="horror",
        )

        prompt = create.call_args.kwargs["input"]
        self.assertIn("Aim for 46 spoken words total.", prompt)
        self.assertIn("Speaking style: sad", prompt)
        self.assertIn("restrained, reflective", prompt)
        self.assertIn("Never add\n  bracketed acting directions", prompt)
        self.assertIn("SELECTED CHARACTER STYLE: horror", prompt)
        self.assertIn("original recurring unsettling horror character", prompt)
        self.assertIn("keep imagery non-graphic", prompt)

    @patch("main.genai.Client")
    def test_story_prompt_uses_loaded_niche_and_research(self, client_class):
        response = {
            "title": "Test Story",
            "character_bible": "A fictional scientist in a blue coat.",
            "visual_style": "Detailed laboratory photography.",
            "scenes": [
                {
                    "retention_beat": "Hook — introduce the unexplained result.",
                    "narration": "A short line.",
                    "visual_anchor": "A scientist examines a laboratory sample.",
                    "stock_queries": [
                        "scientist examining laboratory sample",
                        "researcher working laboratory",
                    ],
                    "image_prompt": "A scientist examining a laboratory sample.",
                },
                {
                    "retention_beat": "Payoff — reveal the discovery.",
                    "narration": "The final line.",
                    "visual_anchor": "The scientist sees the experiment succeed.",
                    "stock_queries": [
                        "scientist successful experiment",
                        "happy researcher laboratory",
                    ],
                    "image_prompt": "A scientist watching the successful experiment.",
                },
            ],
        }
        create = Mock(
            return_value=SimpleNamespace(output_text=json.dumps(response))
        )
        client_class.return_value.interactions.create = create
        profile = load_niche_profile("science")
        brief = ResearchBrief(
            topic="A discovery",
            niche_id=profile.id,
            query="A discovery evidence",
            researched_at="2026-01-01T00:00:00+00:00",
            sources=[
                ResearchSource(
                    title="Research source",
                    url="https://example.com/research",
                    snippet="A verified summary.",
                    extracted_text="The experiment measured a repeatable effect.",
                )
            ],
        )

        main.generate_story(
            api_key="test-key",
            topic="A discovery",
            language="English",
            target_seconds=20,
            scene_count=2,
            niche_profile=profile,
            research_brief=brief,
        )

        prompt = create.call_args.kwargs["input"]
        self.assertIn("NICHE: Science (science)", prompt)
        self.assertIn("Wonder-driven, clear, skeptical", prompt)
        self.assertIn("SOURCE 1", prompt)
        self.assertIn("https://example.com/research", prompt)
        self.assertIn("UNTRUSTED reference data", prompt)
        self.assertIn("Do not invent dates, quotes, statistics", prompt)
        self.assertIn("STORY CLARITY AND AUDIENCE RETENTION", prompt)
        self.assertIn("one visually coherent beat", prompt)
        self.assertIn("close the opening information gap", prompt)
        self.assertIn("CAPTION-TO-IMAGE ALIGNMENT", prompt)
        self.assertIn("GENERATED-IMAGE METHOD", prompt)
        self.assertNotIn("STOCK-PHOTO VISUAL METHOD", prompt)

    @patch("main.genai.Client")
    def test_storyteller_keeps_the_selected_niche_and_story_structure(
        self,
        client_class,
    ):
        response = {
            "title": "A Reef After Dark",
            "character_bible": "A consistent tropical reef habitat after sunset.",
            "visual_style": "Natural underwater wildlife photography.",
            "scenes": [
                {
                    "retention_beat": "Hook.",
                    "narration": "At sunset, the reef changes shifts.",
                    "visual_anchor": "A coral reef as nocturnal fish emerge.",
                    "stock_queries": [
                        "coral reef nocturnal fish",
                        "reef underwater night",
                    ],
                    "image_prompt": "Nocturnal fish emerge over a coral reef.",
                },
                {
                    "retention_beat": "Payoff.",
                    "narration": "Coral polyps extend their tentacles to feed.",
                    "visual_anchor": "Coral polyps feeding in dark ocean water.",
                    "stock_queries": [
                        "coral polyps feeding night",
                        "coral macro underwater",
                    ],
                    "image_prompt": "Macro photograph of feeding coral polyps.",
                },
            ],
        }
        create = Mock(
            return_value=SimpleNamespace(output_text=json.dumps(response))
        )
        client_class.return_value.interactions.create = create

        main.generate_story(
            api_key="test-key",
            topic="How coral reefs change after sunset",
            language="English",
            target_seconds=20,
            scene_count=2,
            niche_profile=load_niche_profile("business-marketing"),
        )

        prompt = create.call_args.kwargs["input"]
        self.assertIn("NICHE PROFILE —", prompt)
        self.assertIn("NICHE: Business and Marketing", prompt)
        self.assertIn("GENERATED-IMAGE METHOD", prompt)
        self.assertIn("hook → context → escalation → turning point → payoff", prompt)
        self.assertNotIn("STOCK-PHOTO VISUAL METHOD", prompt)

    @patch("main.genai.Client")
    def test_generated_mode_does_not_force_a_human_character(
        self,
        client_class,
    ):
        response = {
            "title": "Bread Takes Shape",
            "character_bible": "Consistent dough, wooden bench, and bakery light.",
            "visual_style": "Warm close-up food photography.",
            "scenes": [
                {
                    "retention_beat": "Open on the transformation.",
                    "narration": "Folding gives the dough structure.",
                    "visual_anchor": "Hands folding dough on a wooden bench.",
                    "stock_queries": [
                        "hands folding bread dough",
                        "bread dough bench",
                    ],
                    "image_prompt": "Hands fold bread dough on a wooden bench.",
                },
                {
                    "retention_beat": "Show the result.",
                    "narration": "The shaped loaf can now rise evenly.",
                    "visual_anchor": "A shaped loaf resting in a proofing basket.",
                    "stock_queries": [
                        "loaf proofing basket",
                        "bread dough rising",
                    ],
                    "image_prompt": "A shaped loaf rests in a proofing basket.",
                },
            ],
        }
        create = Mock(
            return_value=SimpleNamespace(output_text=json.dumps(response))
        )
        client_class.return_value.interactions.create = create

        main.generate_story(
            api_key="test-key",
            topic="How to shape bread dough",
            language="English",
            target_seconds=20,
            scene_count=2,
        )

        prompt = create.call_args.kwargs["input"]
        self.assertIn("species, an object, a", prompt)
        self.assertIn("Do not force a human protagonist", prompt)
        self.assertIn(
            "chronological,\n  spatial, comparative, or step-by-step",
            prompt,
        )
        self.assertNotIn("Create one fictional main character", prompt)

    def test_parser_has_no_topic_explainer_or_stock_options(self):
        args = main.build_parser().parse_args(["A test topic"])

        self.assertFalse(hasattr(args, "visual_source"))
        self.assertFalse(hasattr(args, "stock_results"))

    @patch("main.generate_image")
    def test_scene_prompt_adds_detailed_visual_direction(self, generate_image):
        plan = main.StoryPlan(
            title="Test",
            character_bible="A traveler with a red wool coat and silver watch.",
            visual_style="Low-key tungsten light with a cool blue color grade.",
            scenes=[
                main.Scene(
                    retention_beat="Orientation — establish the abandoned station.",
                    narration="The traveler stops.",
                    visual_anchor=(
                        "The traveler stops in front of an abandoned station."
                    ),
                    stock_queries=[
                        "traveler abandoned train station",
                        "person old railway station",
                    ],
                    image_prompt="The traveler studies an abandoned station.",
                ),
                main.Scene(
                    retention_beat="Turning point — the impossible train arrives.",
                    narration="A train arrives.",
                    visual_anchor=(
                        "An old train emerges while the traveler watches."
                    ),
                    stock_queries=[
                        "old train fog traveler",
                        "vintage train fog",
                    ],
                    image_prompt="An old train emerges through fog.",
                ),
            ],
        )

        with tempfile.TemporaryDirectory() as temporary_directory:
            main.generate_scene_images(
                client=Mock(),
                plan=plan,
                images_dir=Path(temporary_directory),
                image_model="test/model",
                base_seed=10,
                character_style="animal",
            )

        prompt = generate_image.call_args_list[0].kwargs["prompt"]
        self.assertIn("SCENE 1 OF 2", prompt)
        self.assertIn("EXACT ON-SCREEN NARRATION", prompt)
        self.assertIn("The traveler stops.", prompt)
        self.assertIn("MANDATORY VISUAL ANCHOR", prompt)
        self.assertIn(
            "The traveler stops in front of an abandoned station.",
            prompt,
        )
        self.assertIn("first priority is semantic alignment", prompt)
        self.assertIn("do not substitute a generic", prompt)
        self.assertIn("SUBJECT AND WORLD CONTINUITY", prompt)
        self.assertIn("foreground, midground, and background", prompt)
        self.assertIn("natural anatomy", prompt)
        self.assertIn("No text, captions", prompt)
        self.assertIn("SELECTED CHARACTER STYLE", prompt)
        self.assertIn("Character-led animal animation", prompt)
        self.assertIn("consistent markings", prompt)


class VideoCommandTests(unittest.TestCase):
    @patch("main.require_audio_stream")
    @patch("main.run_command")
    def test_narration_master_uses_original_audio_files(
        self, run_command, require_audio_stream
    ):
        audio_paths = [Path("audio/one.mp3"), Path("audio/two.mp3")]
        output_path = Path("outputs/narration.wav")

        main.build_narration_track(audio_paths, output_path)

        command = run_command.call_args.args[0]
        audio_filter = command[command.index("-filter_complex") + 1]
        self.assertIn("concat=n=2:v=0:a=1", audio_filter)
        self.assertIn(main.NARRATION_LOUDNESS_FILTER, audio_filter)
        self.assertEqual(command[command.index("-c:a") + 1], "pcm_s16le")
        require_audio_stream.assert_called_once_with(output_path)

    @patch("main.run_command")
    def test_scene_renderer_uses_image_and_audio_inputs(self, run_command):
        main.make_scene_video(
            image_path=Path("images/scene.png"),
            audio_path=Path("audio/scene.mp3"),
            output_path=Path("clips/scene.mp4"),
            duration=4.5,
        )

        command = run_command.call_args.args[0]
        self.assertIn("images/scene.png", command)
        self.assertIn("audio/scene.mp3", command)
        self.assertNotIn("concat", command)
        self.assertIn("aresample=async=1:first_pts=0", command)
        self.assertIn("make_zero", command)

    @patch("main.probe_duration", return_value=60.0)
    @patch("main.run_command")
    def test_gameplay_renderer_loops_and_center_crops_vertical_video(
        self,
        run_command,
        probe_duration,
    ):
        start = main.make_gameplay_video(
            gameplay_path=Path("gameplay/parkour.mp4"),
            output_path=Path("outputs/joined.mp4"),
            duration=20.0,
            seed=7,
        )

        command = run_command.call_args.args[0]
        video_filter = command[command.index("-vf") + 1]
        self.assertIn("-stream_loop", command)
        self.assertIn("-an", command)
        self.assertIn("scale=1080:1920", video_filter)
        self.assertIn("crop=1080:1920", video_filter)
        self.assertIn("fps=60", video_filter)
        self.assertEqual(command[command.index("-t") + 1], "20.000")
        self.assertGreaterEqual(start, 0.0)
        self.assertLessEqual(start, 40.0)
        probe_duration.assert_called_once_with(Path("gameplay/parkour.mp4"))

    def test_gameplay_directory_selection_is_seeded(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            gameplay_dir = Path(temporary_directory)
            for name in ("one.mp4", "two.mp4", "ignore.txt"):
                (gameplay_dir / name).touch()

            first = main.select_gameplay_video(gameplay_dir, seed=42)
            second = main.select_gameplay_video(gameplay_dir, seed=42)

        self.assertEqual(first, second)
        self.assertEqual(first.suffix, ".mp4")

    def test_speaking_profiles_are_slow_and_can_be_overridden(self):
        serious = main.build_voice_settings("serious")
        excited = main.build_voice_settings("excited")
        overridden = main.build_voice_settings("mysterious", 0.75)

        self.assertLess(serious.speed, 1.0)
        self.assertLess(excited.speed, 1.0)
        self.assertEqual(overridden.speed, 0.75)
        self.assertGreater(
            main.build_voice_settings("angry").style,
            serious.style,
        )
        with self.assertRaisesRegex(ValueError, "between 0.7 and 1.2"):
            main.build_voice_settings("sad", 0.6)

    def test_parser_accepts_speaking_style_and_speed(self):
        args = main.build_parser().parse_args(
            [
                "A test topic",
                "--speaking-style",
                "mysterious",
                "--speech-speed",
                "0.8",
            ]
        )

        self.assertEqual(args.speaking_style, "mysterious")
        self.assertEqual(args.speech_speed, 0.8)

    def test_parser_accepts_character_styles_and_sims_alias(self):
        life_sim = main.build_parser().parse_args(
            ["A test topic", "--character-style", "sims"]
        )
        animated_human = main.build_parser().parse_args(
            ["A test topic", "--character-style", "animated-human"]
        )

        self.assertEqual(life_sim.character_style, "life-sim")
        self.assertEqual(animated_human.character_style, "animated-human")
        self.assertIn("no game UI", main.CHARACTER_STYLE_PROFILES["life-sim"].render_direction)

    @patch("main.run_command")
    def test_concat_reencodes_and_normalizes_timestamps(self, run_command):
        with tempfile.TemporaryDirectory() as temporary_directory:
            clips_dir = Path(temporary_directory) / "clips"
            clips_dir.mkdir()
            clips = [clips_dir / "one.mp4", clips_dir / "two.mp4"]
            output_path = Path(temporary_directory) / "joined.mp4"

            main.concat_scene_videos(clips, output_path)

            command = run_command.call_args.args[0]
            self.assertNotIn("copy", command)
            self.assertIn("aresample=async=1:first_pts=0", command)
            self.assertIn("make_zero", command)
            self.assertEqual(run_command.call_args.kwargs["cwd"], clips_dir)
            self.assertEqual(
                (clips_dir / "concat.txt").read_text(encoding="utf-8"),
                "file 'one.mp4'\nfile 'two.mp4'\n",
            )

    def test_concat_rejects_an_empty_clip_list(self):
        with self.assertRaisesRegex(ValueError, "At least one"):
            main.concat_scene_videos([], Path("joined.mp4"))

    @patch("main.probe_duration", return_value=12.5)
    @patch("main.run_command")
    def test_music_mix_uses_source_duration_instead_of_shortest(
        self, run_command, probe_duration
    ):
        run_dir = Path("outputs/run")
        main.finalize_video(
            joined_video=run_dir / "joined.mp4",
            narration_path=run_dir / "narration.wav",
            subtitles_path=run_dir / "subtitles.srt",
            output_path=run_dir / "final.mp4",
            music_path=Path("music.mp3"),
        )

        command = run_command.call_args.args[0]
        self.assertNotIn("-shortest", command)
        self.assertEqual(command[command.index("-t") + 1], "12.500")
        self.assertIn("normalize=0", command[command.index("-filter_complex") + 1])
        self.assertIn(
            "aresample=async=1:first_pts=0[mixed]",
            command[command.index("-filter_complex") + 1],
        )
        probe_duration.assert_called_once_with(run_dir / "joined.mp4")

    @patch("main.probe_duration", return_value=12.5)
    @patch("main.run_command")
    def test_final_video_explicitly_maps_and_normalizes_narration(
        self, run_command, probe_duration
    ):
        run_dir = Path("outputs/run")
        main.finalize_video(
            joined_video=run_dir / "joined.mp4",
            narration_path=run_dir / "narration.wav",
            subtitles_path=run_dir / "subtitles.srt",
            output_path=run_dir / "final.mp4",
            music_path=None,
        )

        command = run_command.call_args.args[0]
        self.assertIn("1:a:0", command)
        self.assertIn("narration.wav", command)
        self.assertEqual(command[command.index("-c:a") + 1], "aac")
        self.assertIn("-disposition:a:0", command)
        subtitle_filter = command[command.index("-vf") + 1]
        self.assertIn("FontSize=11", subtitle_filter)
        self.assertIn("BorderStyle=3", subtitle_filter)
        self.assertIn("Outline=1.5", subtitle_filter)
        self.assertIn("MarginV=12", subtitle_filter)
        probe_duration.assert_called_once_with(run_dir / "joined.mp4")

    @patch("main.probe_duration", return_value=12.5)
    @patch("main.run_command")
    def test_ass_subtitles_keep_their_animated_embedded_style(
        self,
        run_command,
        probe_duration,
    ):
        run_dir = Path("outputs/run")
        main.finalize_video(
            joined_video=run_dir / "joined.mp4",
            narration_path=run_dir / "narration.wav",
            subtitles_path=run_dir / "subtitles.ass",
            output_path=run_dir / "final.mp4",
            music_path=None,
        )

        command = run_command.call_args.args[0]
        subtitle_filter = command[command.index("-vf") + 1]
        self.assertEqual(subtitle_filter, "subtitles=filename='subtitles.ass'")
        self.assertNotIn("force_style", subtitle_filter)


class SubtitleTests(unittest.TestCase):
    def test_caption_chunks_stay_compact(self):
        self.assertEqual(
            main.caption_chunks("one two three four five six seven"),
            ["one two three four five", "six seven"],
        )

    def test_subtitle_timeline_is_continuous_across_scenes(self):
        plan = main.StoryPlan(
            title="Test",
            character_bible="A fictional person.",
            visual_style="Cinematic.",
            scenes=[
                main.Scene(
                    retention_beat="Hook.",
                    narration="One two three.",
                    visual_anchor="A person sees the first event.",
                    stock_queries=["person watching event", "surprised observer"],
                    image_prompt="First.",
                ),
                main.Scene(
                    retention_beat="Payoff.",
                    narration="Four five six.",
                    visual_anchor="A person sees the second event.",
                    stock_queries=["person second event", "person observing"],
                    image_prompt="Second.",
                ),
            ],
        )

        with tempfile.TemporaryDirectory() as temporary_directory:
            output_path = Path(temporary_directory) / "subtitles.srt"
            main.write_subtitles(
                plan=plan,
                durations=[1.25, 2.0],
                output_path=output_path,
            )
            subtitles = output_path.read_text(encoding="utf-8")

        self.assertIn("00:00:00,000 --> 00:00:01,250", subtitles)
        self.assertIn("00:00:01,250 --> 00:00:03,250", subtitles)

    def test_gameplay_subtitles_use_exact_word_timing_and_smooth_highlight(self):
        plan = main.StoryPlan(
            title="Test",
            character_bible="Not used in game mode.",
            visual_style="Not used in game mode.",
            scenes=[
                main.Scene(
                    retention_beat="Hook.",
                    narration="Smooth words now.",
                    visual_anchor="Not used in game mode.",
                    image_prompt="Not used in game mode.",
                )
            ],
        )
        characters = list("Smooth words now.")
        starts = [index * 0.1 for index in range(len(characters))]
        ends = [(index + 1) * 0.1 for index in range(len(characters))]

        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_path = Path(temporary_directory)
            alignment_path = temporary_path / "alignment.json"
            alignment_path.write_text(
                json.dumps(
                    {
                        "characters": characters,
                        "character_start_times_seconds": starts,
                        "character_end_times_seconds": ends,
                    }
                ),
                encoding="utf-8",
            )
            output_path = temporary_path / "subtitles.ass"
            main.write_gameplay_subtitles(
                plan=plan,
                durations=[2.0],
                alignment_paths=[alignment_path],
                output_path=output_path,
            )
            subtitles = output_path.read_text(encoding="utf-8")

        self.assertIn("PlayResX: 1080", subtitles)
        self.assertIn("PlayResY: 1920", subtitles)
        self.assertIn("GameCaption,DejaVu Sans,82", subtitles)
        self.assertIn(r"\an5\pos(540,960)", subtitles)
        self.assertIn(r"\t(0,90,\fscx112\fscy112)", subtitles)
        self.assertIn(r"\c&H0000D7FF&", subtitles)
        self.assertIn("Dialogue: 0,0:00:00.00,0:00:00.70", subtitles)

    def test_parser_exposes_video_game_mode_and_default_gameplay_library(self):
        args = main.build_parser().parse_args(
            ["A test topic", "--video-game-mode"]
        )

        self.assertTrue(args.video_game_mode)
        self.assertEqual(args.gameplay_video, main.DEFAULT_GAMEPLAY_SOURCE)


class GeminiImageProviderTests(unittest.TestCase):
    def test_gemini_image_response_is_written_from_inline_data(self):
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def read(self):
                return json.dumps(
                    {
                        "candidates": [
                            {
                                "content": {
                                    "parts": [
                                        {
                                            "inlineData": {
                                                "mimeType": "image/png",
                                                "data": "aW1hZ2U=",
                                            }
                                        }
                                    ]
                                }
                            }
                        ]
                    }
                ).encode("utf-8")

        with tempfile.TemporaryDirectory() as temporary_directory:
            output_path = Path(temporary_directory) / "gemini.png"
            with patch(
                "main.urllib.request.urlopen",
                return_value=FakeResponse(),
            ) as urlopen:
                main.generate_gemini_image(
                    api_key="secret-key",
                    model="gemini-2.5-flash-image",
                    prompt="A vertical cinematic lighthouse",
                    output_path=output_path,
                    seed=None,
                    model_config={
                        "responseModalities": ["IMAGE"],
                        "responseFormat": {
                            "image": {"aspectRatio": "9:16"}
                        },
                    },
                )

            self.assertEqual(output_path.read_bytes(), b"image")
            request = urlopen.call_args.args[0]
            self.assertIn("gemini-2.5-flash-image", request.full_url)
            self.assertEqual(
                request.headers["X-goog-api-key"],
                "secret-key",
            )
            body = json.loads(request.data.decode("utf-8"))
            self.assertEqual(
                body["generationConfig"]["responseFormat"]["image"][
                    "aspectRatio"
                ],
                "9:16",
            )


if __name__ == "__main__":
    unittest.main()
