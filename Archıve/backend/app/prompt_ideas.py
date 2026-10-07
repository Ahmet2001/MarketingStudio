from __future__ import annotations

import os
import re
from secrets import choice

import httpx
from dotenv import dotenv_values

from .config import EXPLAINER_ROOT, STORYTELLER_ROOT


PROMPT_MODEL = os.getenv(
    "STORYFORGE_PROMPT_MODEL", "gemini-3.5-flash-lite"
)
PROMPT_AI_ENABLED = os.getenv(
    "STORYFORGE_PROMPT_AI_ENABLED", "true"
).lower() in {"1", "true", "yes"}

MODE_DIRECTIONS = {
    "ai-photos": (
        "an emotionally compelling fictional story with a strong visual hook, "
        "a clear protagonist, and a surprising but satisfying turn"
    ),
    "reddit": (
        "a first-person Reddit-style confession or dilemma that starts with an "
        "irresistible hook and ends with a believable twist"
    ),
    "real-images": (
        "a grounded true-story or human-interest idea that can be illustrated "
        "with authentic, sourceable photographs"
    ),
    "documentary": (
        "an overlooked historical event, invention, rivalry, or turning point "
        "that can be explained accurately with archival visuals"
    ),
    "stock-explainer": (
        "a useful how-it-works or surprising science idea suited to stock footage"
    ),
    "avatar": (
        "a concise tutorial, product insight, or practical list for a presenter"
    ),
}

FALLBACK_IDEAS = {
    "ai-photos": (
        "A night-shift train conductor finds a handwritten ticket dated tomorrow, "
        "warning him not to stop at the final station.",
        "An elderly lighthouse keeper receives one last radio message from the "
        "rescue boat that saved him forty years earlier.",
        "A shy street photographer discovers that every stranger in her pictures "
        "is looking toward the same person no one else can see.",
    ),
    "reddit": (
        "I agreed to housesit for my sister, but her one strange rule about the "
        "basement made sense only after midnight.",
        "My coworker kept taking credit for my ideas, so I let him present the one "
        "project I knew he could not explain.",
        "I found out why my neighbor moved my trash bin every Tuesday, and now I "
        "owe him an apology I am afraid to make.",
    ),
    "real-images": (
        "How a small coastal town rebuilt its only school after a storm—and the "
        "teacher whose photo diary preserved every step.",
        "The true story of a family bakery that survived three generations by "
        "keeping one unusual promise to its neighborhood.",
        "Follow the volunteers restoring an abandoned railway station and the "
        "forgotten photographs that revealed its original colors.",
    ),
    "documentary": (
        "How the 1859 Carrington Event made telegraph machines spark—and what a "
        "similar solar storm could mean today.",
        "The forgotten race to standardize time zones and why railway schedules "
        "forced cities to change their clocks.",
        "How a volcanic eruption in 1815 created the Year Without a Summer and "
        "reshaped food, migration, and literature.",
    ),
    "stock-explainer": (
        "Why undersea cables carry nearly all international internet traffic and "
        "how repair ships find a break on the ocean floor.",
    ),
    "avatar": (
        "Three small changes that make a product update clearer, faster, and more "
        "useful to customers.",
    ),
}


def _gemini_api_key() -> str:
    configured = os.getenv("GEMINI_API_KEY", "").strip()
    if configured:
        return configured
    for environment_file in (
        STORYTELLER_ROOT / ".env",
        EXPLAINER_ROOT / ".env",
    ):
        if environment_file.is_file():
            value = str(
                dotenv_values(environment_file).get("GEMINI_API_KEY") or ""
            ).strip()
            if value:
                return value
    return ""


def _fallback(mode_id: str) -> str:
    return choice(FALLBACK_IDEAS[mode_id])


def _clean_idea(value: str) -> str:
    idea = re.sub(r"\s+", " ", value).strip()
    idea = re.sub(
        r"^(idea|prompt|video idea)\s*:\s*",
        "",
        idea,
        flags=re.IGNORECASE,
    )
    idea = idea.strip("`\"' ")
    if len(idea) > 500:
        idea = idea[:500].rsplit(" ", 1)[0].rstrip(" ,;:-") + "…"
    return idea


async def create_lucky_prompt(
    *,
    mode_id: str,
    language: str,
    niche: str,
) -> tuple[str, str]:
    fallback = _fallback(mode_id)
    api_key = _gemini_api_key()
    if not PROMPT_AI_ENABLED or not api_key:
        return fallback, "fallback"

    direction = MODE_DIRECTIONS[mode_id]
    instruction = f"""
You are the idea editor for a premium short-form video studio.

Invent exactly one original video brief for {direction}.
The selected niche is "{niche}".
Write it in {language}.

Requirements:
- 20 to 45 words and no more than 500 characters.
- Specific enough to inspire a strong opening hook and 4 to 10 visual scenes.
- Fresh, emotionally engaging, brand-safe, and non-graphic.
- If factual, make it concrete and realistically fact-checkable.
- Return only the brief. No title, quotation marks, label, or explanation.
""".strip()

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                (
                    "https://generativelanguage.googleapis.com/v1beta/models/"
                    f"{PROMPT_MODEL}:generateContent"
                ),
                headers={"x-goog-api-key": api_key},
                json={
                    "contents": [
                        {"role": "user", "parts": [{"text": instruction}]}
                    ]
                },
            )
        response.raise_for_status()
        payload = response.json()
        value = payload["candidates"][0]["content"]["parts"][0]["text"]
        idea = _clean_idea(str(value))
        if len(idea) >= 20:
            return idea, "ai"
    except (
        httpx.HTTPError,
        KeyError,
        IndexError,
        TypeError,
        ValueError,
    ):
        pass
    return fallback, "fallback"
