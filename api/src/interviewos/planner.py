from __future__ import annotations

from interviewos.constants import (
    DEFAULT_QUESTION_COUNT,
    DIFFICULTY_LADDER,
    ETHICAL_GUARDRAILS,
    MAX_QUESTION_COUNT,
    STEM_TYPES,
)
from interviewos.models import InterviewConfig, InterviewPlan


def plan_interview(config: InterviewConfig, *, live: bool = False) -> InterviewPlan:
    if live:
        try:
            from interviewos.claude import plan_interview_live

            return plan_interview_live(config)
        except Exception:
            return mock_plan_interview(config)
    return mock_plan_interview(config)


def mock_plan_interview(config: InterviewConfig) -> InterviewPlan:
    user_mode = config.interview_mode or "Auto"
    user_diff = config.difficulty or "Auto"
    interview_type = config.interview_type
    opp = (config.opportunity_description or "").lower()
    bg = (config.applicant_background or "").lower()
    full = f"{opp} {bg}"

    if user_mode != "Auto":
        resolved_mode = user_mode
    elif interview_type in STEM_TYPES:
        resolved_mode = "Mixed"
    else:
        tech_kw = {
            "code",
            "algorithm",
            "data structure",
            "model",
            "modeling",
            "research",
            "compute",
            "ml",
            "machine learning",
            "statistics",
            "python",
            "scientific",
            "math",
            "quantitative",
        }
        resolved_mode = "Mixed" if any(k in full for k in tech_kw) else "Qualitative"

    if user_diff != "Auto":
        resolved_difficulty = user_diff if user_diff in DIFFICULTY_LADDER else "Intermediate"
    elif any(k in full for k in ["beginner", "first", "early", "no experience", "new to"]):
        resolved_difficulty = "Beginner"
    elif any(k in full for k in ["intense", "expert", "principal"]):
        resolved_difficulty = "Intense"
    elif any(k in full for k in ["phd", "senior", "graduate", "advanced"]):
        resolved_difficulty = "Advanced"
    else:
        resolved_difficulty = "Intermediate"

    if isinstance(config.question_count, int) and config.question_count > 0:
        resolved_n = config.question_count
    elif resolved_difficulty in {"Advanced", "Intense"}:
        resolved_n = 5
    else:
        resolved_n = DEFAULT_QUESTION_COUNT
    resolved_n = max(1, min(MAX_QUESTION_COUNT, resolved_n))

    resolved_timer = (
        config.timer_seconds
        if isinstance(config.timer_seconds, int) and config.timer_seconds > 0
        else None
    )

    why_mode = (
        f"the {interview_type} interview type"
        if interview_type in STEM_TYPES
        else "the description you provided"
        if (opp or bg)
        else "a sensible default"
    )
    rationale = (
        f"Planned a {resolved_mode.lower()} interview at "
        f"{resolved_difficulty.lower()} difficulty, {resolved_n} questions"
        + (f", {resolved_timer}s timer per question" if resolved_timer else ", no timer")
        + f", based on {why_mode}."
    )
    style_notes = (
        "Stay in conversation. Quote the candidate when probing. "
        "Difficulty changes both question banks and how hard you push. "
        "Technical items must include an answer key stored only on the server."
    )
    return InterviewPlan(
        resolved_mode=resolved_mode,
        resolved_difficulty=resolved_difficulty,
        resolved_question_count=resolved_n,
        resolved_timer_seconds=resolved_timer,
        rationale=rationale,
        question_style_notes=style_notes,
    )


def plan_system_prompt() -> str:
    return (
        ETHICAL_GUARDRAILS
        + "\nYou are designing the structure of a mock interview.\n"
        "Pick interview mode, difficulty, question count, and timer based "
        "on the user's interview type, description, and background. If the "
        "user already chose a non-Auto value, RESPECT IT.\n\n"
        "Constraints:\n"
        "- resolved_mode in {Qualitative, Technical, Mixed}\n"
        "- resolved_difficulty in {Beginner, Intermediate, Advanced, Intense}\n"
        "- resolved_question_count: integer 1-10 (use 3 if uncertain)\n"
        "- resolved_timer_seconds: integer (e.g. 30, 60, 90, 120) or null\n"
        "- For Technical SWE, Quant / Trading, Scientific Computing, Data Science, "
        "or Research Program, prefer Mixed unless told otherwise.\n"
    )
