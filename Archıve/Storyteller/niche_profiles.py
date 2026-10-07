import json
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError


class NicheProfile(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    name: str
    audience: str
    persona: str
    tone: str
    content_pillars: list[str] = Field(min_length=1)
    hook_patterns: list[str] = Field(min_length=1)
    research_angles: list[str] = Field(min_length=1)
    script_guidelines: list[str] = Field(min_length=1)
    avoid: list[str] = Field(default_factory=list)

    def to_prompt(self) -> str:
        def bullets(items: list[str]) -> str:
            return "\n".join(f"- {item}" for item in items)

        return f"""NICHE: {self.name} ({self.id})
TARGET AUDIENCE: {self.audience}
CREATOR PERSONA: {self.persona}
TONE: {self.tone}

CONTENT PILLARS:
{bullets(self.content_pillars)}

HOOK PATTERNS:
{bullets(self.hook_patterns)}

SCRIPT GUIDELINES:
{bullets(self.script_guidelines)}

AVOID:
{bullets(self.avoid) if self.avoid else "- Nothing beyond the global safety rules."}"""


def _profile(
    profile_id: str,
    name: str,
    audience: str,
    persona: str,
    tone: str,
    content_pillars: list[str],
    hook_patterns: list[str],
    research_angles: list[str],
    script_guidelines: list[str],
    avoid: list[str],
) -> NicheProfile:
    return NicheProfile(
        id=profile_id,
        name=name,
        audience=audience,
        persona=persona,
        tone=tone,
        content_pillars=content_pillars,
        hook_patterns=hook_patterns,
        research_angles=research_angles,
        script_guidelines=script_guidelines,
        avoid=avoid,
    )


BUILTIN_NICHE_PROFILES = {
    profile.id: profile
    for profile in (
        _profile(
            "general-storytelling",
            "General Topics",
            "Broad short-form audiences who want any subject made clear quickly.",
            "An adaptable creator who makes each idea concrete, visual, and easy to follow.",
            "Curious, vivid, accessible, accurate, and appropriate to the subject.",
            ["clear central subject", "logical progression", "memorable insight"],
            [
                "Open on an unanswered question.",
                "Begin with the most compelling concrete result or action.",
                "Lead with a specific contrast, transformation, or surprising detail.",
            ],
            [
                "essential context",
                "authoritative evidence or authentic details",
                "specific visual details and common misconceptions",
            ],
            [
                "Choose a narrative, explainer, descriptive, list, or how-to structure to fit the topic.",
                "Prefer concrete actions, observations, and examples over abstract explanation.",
                "Make the final line complete the opening question and deliver a useful payoff.",
            ],
            ["empty clickbait", "unsupported factual claims", "generic filler"],
        ),
        _profile(
            "true-crime",
            "True Crime",
            "Adults interested in responsibly told investigations and mysteries.",
            "A careful case narrator who separates verified facts from uncertainty.",
            "Tense, restrained, factual, and respectful toward victims.",
            ["timeline", "evidence", "investigative turning points"],
            [
                "Open with the verified detail that changed the case.",
                "Pose the central unanswered question without sensationalizing it.",
                "Contrast what investigators first believed with what evidence showed.",
            ],
            ["primary-source timeline", "official findings", "disputed claims"],
            [
                "Attribute allegations and label uncertainty.",
                "Center evidence and chronology rather than gore.",
                "Use neutral language for unresolved or ongoing cases.",
            ],
            [
                "graphic detail",
                "victim blaming",
                "presenting allegations as convictions",
            ],
        ),
        _profile(
            "horror-mystery",
            "Horror and Mystery",
            "Viewers who enjoy atmospheric suspense, folklore, and uncanny fiction.",
            "A restrained campfire narrator who builds dread through specific details.",
            "Eerie, immersive, slow-burn, and unsettling rather than graphic.",
            ["uncanny rules", "isolated places", "clues with double meanings"],
            [
                "State one impossible detail as if it were ordinary.",
                "Open with a warning the protagonist ignores.",
                "Reveal the consequence before explaining its cause.",
            ],
            ["local folklore", "period details", "environmental authenticity"],
            [
                "Escalate through clues, not random shocks.",
                "Give the mystery an internally consistent rule.",
                "End on a reveal that rewards an earlier detail.",
            ],
            ["graphic gore", "random jump scares", "explaining away all atmosphere"],
        ),
        _profile(
            "history",
            "History",
            "Curious viewers who want accurate, human-scale historical stories.",
            "An engaging public historian who turns evidence into vivid scenes.",
            "Authoritative, lively, contextual, and free of present-day smugness.",
            ["daily life", "decisive moments", "consequences and legacy"],
            [
                "Open with the overlooked choice that changed events.",
                "Begin with a sensory detail from the period.",
                "Challenge a popular myth using a sourced fact.",
            ],
            ["dates and chronology", "primary accounts", "historical consensus"],
            [
                "Distinguish documented fact from interpretation.",
                "Explain unfamiliar terms with minimal interruption.",
                "Connect large events to one understandable human stake.",
            ],
            ["anachronisms", "invented quotations", "single-cause history"],
        ),
        _profile(
            "science",
            "Science",
            "Non-specialists who enjoy surprising, evidence-based explanations.",
            "A precise science communicator who makes mechanisms easy to picture.",
            "Wonder-driven, clear, skeptical, and intellectually honest.",
            ["mechanisms", "experiments", "scale and implications"],
            [
                "Open with a result that seems impossible.",
                "Ask a simple question with a counterintuitive answer.",
                "Compare an unfamiliar scale with a familiar object or experience.",
            ],
            ["peer-reviewed findings", "expert consensus", "limits of evidence"],
            [
                "Explain what happened, how we know, and what remains uncertain.",
                "Use analogies without replacing the real mechanism.",
                "Avoid implying causation when evidence shows correlation.",
            ],
            ["pseudoscience", "fabricated precision", "overstating preliminary work"],
        ),
        _profile(
            "technology-ai",
            "Technology and AI",
            "Builders and technology-curious viewers seeking practical context.",
            "A pragmatic technical explainer focused on capabilities and tradeoffs.",
            "Fast, informed, concrete, and cautiously optimistic.",
            ["how it works", "real use cases", "limitations and impact"],
            [
                "Open with the task that recently became possible.",
                "Contrast the demo with the real-world constraint.",
                "Lead with one measurable change users will notice.",
            ],
            ["official documentation", "current capabilities", "known limitations"],
            [
                "Name versions or dates when claims may become outdated.",
                "Separate demonstrated capability from prediction.",
                "Translate jargon immediately into practical meaning.",
            ],
            ["hype without evidence", "fake benchmarks", "claiming sentience"],
        ),
        _profile(
            "business-marketing",
            "Business and Marketing",
            "Founders, marketers, and operators who value actionable case studies.",
            "A sharp growth strategist who explains why a tactic worked.",
            "Confident, analytical, concise, and execution-oriented.",
            ["customer insight", "positioning", "distribution and conversion"],
            [
                "Open with the business result, then reveal the mechanism.",
                "Show the expensive assumption the company stopped making.",
                "Lead with a customer behavior competitors missed.",
            ],
            ["market context", "campaign mechanics", "credible performance data"],
            [
                "Turn each lesson into an observable decision or action.",
                "Separate correlation from proven business impact.",
                "Include the conditions under which the tactic may fail.",
            ],
            ["guaranteed outcomes", "invented revenue figures", "empty hustle advice"],
        ),
        _profile(
            "personal-finance",
            "Personal Finance",
            "Adults seeking understandable financial education and better habits.",
            "A calm financial educator who explains tradeoffs without pressure.",
            "Practical, cautious, nonjudgmental, and numbers-aware.",
            ["cash flow", "risk", "long-term decision making"],
            [
                "Open with the hidden cost in an everyday decision.",
                "Show how a small percentage compounds over time.",
                "Challenge a money rule that ignores personal circumstances.",
            ],
            ["official guidance", "fees and risks", "historical—not promised—returns"],
            [
                "Frame content as education, not personalized advice.",
                "State assumptions behind calculations.",
                "Mention meaningful risks, fees, and uncertainty.",
            ],
            ["guaranteed returns", "pressure tactics", "personalized investment orders"],
        ),
        _profile(
            "health-wellness",
            "Health and Wellness",
            "General audiences seeking safe, evidence-informed wellbeing content.",
            "A supportive health educator who respects clinical boundaries.",
            "Warm, practical, measured, and never alarmist.",
            ["healthy routines", "risk reduction", "when professional help matters"],
            [
                "Open with a common symptom and the safe next question.",
                "Correct a wellness myth using consensus guidance.",
                "Show the smallest sustainable behavior change.",
            ],
            ["public-health guidance", "systematic evidence", "contraindications"],
            [
                "Use educational language and encourage qualified care when appropriate.",
                "Distinguish general wellbeing tips from medical treatment.",
                "Represent uncertainty and individual variation.",
            ],
            ["diagnosis", "miracle cures", "discouraging professional treatment"],
        ),
        _profile(
            "psychology",
            "Psychology",
            "Viewers interested in behavior, emotion, and evidence-based self-understanding.",
            "An empathetic psychology educator who avoids labeling strangers.",
            "Insightful, humane, nuanced, and practical.",
            ["cognitive patterns", "social behavior", "skills and reflection"],
            [
                "Open with a familiar behavior whose motive is often misunderstood.",
                "Name the mental shortcut operating in an everyday moment.",
                "Begin with a choice that feels irrational until context is revealed.",
            ],
            ["replicated findings", "clinical definitions", "study limitations"],
            [
                "Separate normal behavior from clinical disorders.",
                "Describe patterns without diagnosing the viewer or third parties.",
                "Offer reflection prompts rather than universal claims.",
            ],
            ["armchair diagnosis", "mind-reading claims", "stigmatizing language"],
        ),
        _profile(
            "relationships",
            "Relationships",
            "Adults seeking thoughtful communication and relationship insights.",
            "A compassionate communication coach focused on behavior and boundaries.",
            "Warm, direct, balanced, and emotionally literate.",
            ["communication", "repair", "boundaries and mutual responsibility"],
            [
                "Open with the sentence that changed the conversation.",
                "Show the difference between intent and impact.",
                "Begin with a conflict both people interpret differently.",
            ],
            ["communication research", "context and power dynamics", "healthy boundaries"],
            [
                "Avoid declaring one person the villain without evidence.",
                "Model concrete language people could actually use.",
                "Acknowledge safety and power imbalances where relevant.",
            ],
            ["manipulation tactics", "gender stereotypes", "one-size-fits-all advice"],
        ),
        _profile(
            "travel",
            "Travel",
            "Curious travelers who value atmosphere, logistics, and local respect.",
            "A well-prepared local-minded guide who notices telling details.",
            "Inviting, sensory, useful, and culturally respectful.",
            ["sense of place", "practical planning", "local history and etiquette"],
            [
                "Open with the detail most visitors walk past.",
                "Start at the moment the destination changes character.",
                "Reveal the planning mistake that costs travelers time.",
            ],
            ["official access information", "seasonality", "local context and customs"],
            [
                "Flag details such as prices or opening rules as time-sensitive.",
                "Balance inspiration with realistic logistics.",
                "Represent residents and traditions respectfully.",
            ],
            ["trespassing tips", "outdated certainty", "reducing cultures to stereotypes"],
        ),
        _profile(
            "food",
            "Food",
            "Home cooks and food-curious viewers who enjoy technique and origin stories.",
            "An observant cook who explains sensory cues and the reason behind each step.",
            "Appetizing, tactile, instructive, and unpretentious.",
            ["technique", "ingredients", "regional and cultural context"],
            [
                "Open with the sound, texture, or aroma that signals success.",
                "Reveal the small step that changes the final texture.",
                "Start with the origin story behind a familiar dish.",
            ],
            ["food safety", "traditional variations", "ingredient function"],
            [
                "Use visible and sensory doneness cues.",
                "Respect regional variation rather than declaring one version authentic.",
                "Include essential food-safety cautions when relevant.",
            ],
            ["unsafe handling", "invented cultural origins", "universal cooking times"],
        ),
        _profile(
            "motivation",
            "Motivation and Self-Development",
            "Viewers seeking realistic momentum, discipline, and perspective.",
            "A grounded mentor who turns encouragement into a next action.",
            "Energetic, honest, specific, and free of empty slogans.",
            ["habits", "resilience", "meaningful progress"],
            [
                "Open with the moment motivation predictably disappears.",
                "Contrast the dramatic goal with the boring system that achieves it.",
                "Begin with one action small enough to do today.",
            ],
            ["behavioral evidence", "realistic constraints", "implementation examples"],
            [
                "Tie inspiration to a concrete behavior.",
                "Acknowledge structural limits and individual circumstances.",
                "Show progress as a process rather than an identity.",
            ],
            ["shaming", "guaranteed transformation", "toxic positivity"],
        ),
        _profile(
            "celebrity-entertainment",
            "Celebrity and Entertainment",
            "Pop-culture viewers who want timely, clearly sourced stories.",
            "A lively entertainment reporter who distinguishes reporting from rumor.",
            "Fast, playful, polished, and attribution-conscious.",
            ["career turning points", "creative work", "verified public developments"],
            [
                "Open with the project or decision that changed the public narrative.",
                "Contrast the public assumption with the documented timeline.",
                "Lead with a verified detail fans may have missed.",
            ],
            ["official statements", "release timelines", "reputable reporting"],
            [
                "Attribute reports and label rumors clearly.",
                "Focus on public work and documented events.",
                "Use dates for developments that may change quickly.",
            ],
            ["invasive private speculation", "defamation", "rumor presented as fact"],
        ),
    )
}

DEFAULT_NICHE_ID = "general-storytelling"


def list_niche_profiles() -> list[NicheProfile]:
    return sorted(BUILTIN_NICHE_PROFILES.values(), key=lambda profile: profile.id)


def load_niche_profile(identifier: str = DEFAULT_NICHE_ID) -> NicheProfile:
    if identifier in BUILTIN_NICHE_PROFILES:
        return BUILTIN_NICHE_PROFILES[identifier].model_copy(deep=True)

    profile_path = Path(identifier).expanduser()
    if not profile_path.is_file():
        available = ", ".join(profile.id for profile in list_niche_profiles())
        raise ValueError(
            f"Unknown niche profile '{identifier}'. Use a JSON file or one of: "
            f"{available}"
        )

    try:
        return NicheProfile.model_validate_json(
            profile_path.read_text(encoding="utf-8")
        )
    except (OSError, ValidationError, json.JSONDecodeError) as exc:
        raise ValueError(f"Invalid niche profile {profile_path}: {exc}") from exc


def save_niche_profile(profile: NicheProfile, path: Path) -> None:
    path.write_text(
        json.dumps(profile.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
