import os
from pathlib import Path


TEST_RUNTIME = Path(__file__).parent / ".runtime"
os.environ["STORYFORGE_RUNTIME_DIR"] = str(TEST_RUNTIME)
os.environ["STORYFORGE_TASKS_EAGER"] = "true"
os.environ["STORYFORGE_MOCK_GENERATION"] = "true"
os.environ["STORYFORGE_MOCK_STEP_SECONDS"] = "0"
os.environ["STORYFORGE_MOCK_CONNECTIONS"] = "true"
os.environ["STORYFORGE_PROMPT_AI_ENABLED"] = "false"
