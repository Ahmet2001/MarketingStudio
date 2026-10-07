import json
import tempfile
import unittest
from pathlib import Path

from niche_profiles import (
    DEFAULT_NICHE_ID,
    list_niche_profiles,
    load_niche_profile,
)


class NicheProfileTests(unittest.TestCase):
    def test_fifteen_builtin_profiles_are_available(self):
        profiles = list_niche_profiles()

        self.assertEqual(len(profiles), 15)
        self.assertEqual(len({profile.id for profile in profiles}), 15)
        self.assertIn(DEFAULT_NICHE_ID, {profile.id for profile in profiles})

    def test_builtin_profile_is_returned_as_an_independent_copy(self):
        first = load_niche_profile("history")
        first.hook_patterns.append("Temporary test hook.")
        second = load_niche_profile("history")

        self.assertNotIn("Temporary test hook.", second.hook_patterns)

    def test_custom_json_profile_can_be_loaded(self):
        payload = {
            "id": "architecture",
            "name": "Architecture",
            "audience": "Design-curious viewers.",
            "persona": "A precise architectural guide.",
            "tone": "Visual and informed.",
            "content_pillars": ["materials"],
            "hook_patterns": ["Open with a hidden structural detail."],
            "research_angles": ["architect and construction date"],
            "script_guidelines": ["Connect form to function."],
            "avoid": ["invented attribution"],
        }

        with tempfile.TemporaryDirectory() as temporary_directory:
            profile_path = Path(temporary_directory) / "profile.json"
            profile_path.write_text(json.dumps(payload), encoding="utf-8")
            profile = load_niche_profile(str(profile_path))

        self.assertEqual(profile.id, "architecture")
        self.assertEqual(profile.content_pillars, ["materials"])

    def test_unknown_profile_lists_valid_choices(self):
        with self.assertRaisesRegex(ValueError, "general-storytelling"):
            load_niche_profile("does-not-exist")


if __name__ == "__main__":
    unittest.main()
