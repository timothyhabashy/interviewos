from __future__ import annotations

import os
import re

DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-5-20250929"
DEFAULT_QUESTION_COUNT = 3
MAX_QUESTION_COUNT = 10

INTERVIEW_MODES = ["Auto", "Qualitative", "Technical", "Mixed"]
RESOLVED_INTERVIEW_MODES = ["Qualitative", "Technical", "Mixed"]

INTERVIEW_TYPES = [
    "Internship",
    "Scholarship",
    "Research Program",
    "College / Transfer",
    "First Job",
    "Technical SWE",
    "Quant / Trading",
    "Scientific Computing",
    "Data Science",
    "Custom",
]

DIFFICULTY_LEVELS = ["Auto", "Beginner", "Intermediate", "Advanced", "Intense"]
RESOLVED_DIFFICULTY_LEVELS = ["Beginner", "Intermediate", "Advanced", "Intense"]
DIFFICULTY_LADDER = ["Beginner", "Intermediate", "Advanced", "Intense"]

STEM_TYPES = {
    "Technical SWE",
    "Quant / Trading",
    "Scientific Computing",
    "Data Science",
    "Research Program",
}

QUESTION_COUNT_OPTIONS: dict[str, int | None] = {
    "Auto": None,
    "3": 3,
    "5": 5,
    "7": 7,
    "10": 10,
}
TIMER_OPTIONS: dict[str, int | None] = {
    "Off": None,
    "30 seconds / question": 30,
    "60 seconds / question": 60,
    "90 seconds / question": 90,
    "120 seconds / question": 120,
}

RUBRIC_CATEGORIES = [
    ("clarity", "Clarity"),
    ("specificity", "Specificity"),
    ("confidence", "Confidence"),
    ("relevance", "Relevance"),
    ("authenticity", "Authenticity"),
    ("structure", "Structure"),
    ("evidence_examples", "Evidence & Examples"),
    ("growth_mindset", "Growth Mindset"),
    ("technical_reasoning", "Technical Reasoning"),
    ("technical_correctness", "Technical Correctness"),
]
QUALITATIVE_RUBRIC_KEYS = [
    "clarity",
    "specificity",
    "confidence",
    "relevance",
    "authenticity",
    "structure",
    "evidence_examples",
    "growth_mindset",
]
TECHNICAL_RUBRIC_KEYS = ["technical_reasoning", "technical_correctness"]

HEDGE_PATTERN = re.compile(
    r"\b(I guess|I think|I mean|I suppose|kind of|kinda|sort of|sorta|"
    r"basically|just|maybe|really|very|probably|somewhat|honestly|"
    r"a little bit|a bit|a little)\b",
    re.IGNORECASE,
)
EVIDENCE_PATTERN = re.compile(
    r"\b(\d+|project|projects|built|wrote|coded|made|led|won|class|course|"
    r"lab|paper|research|published|presented|shipped|repo|prototype|design)\b",
    re.IGNORECASE,
)
MOTIVATION_PATTERN = re.compile(
    r"\b(because|so that|in order to|matters|care|excited|interested|"
    r"passionate|drives me|drew me|hope to|want to)\b",
    re.IGNORECASE,
)
LEARNING_PATTERN = re.compile(
    r"\b(learned|realized|figured out|mistake|wrong|next time|differently|"
    r"changed|grew|improved|reflected|takeaway)\b",
    re.IGNORECASE,
)
STRUCTURE_PATTERN = re.compile(
    r"\b(first|then|finally|after that|so I|the result|the outcome|"
    r"in the end|what I did|next|eventually|to start|by the end)\b",
    re.IGNORECASE,
)
PROJECT_VERB_PATTERN = re.compile(
    r"(built|wrote|coded|made|led|created|launched|designed|presented|"
    r"won|published|shipped)\s+"
    r"(?:a |an |the )?"
    r"([A-Za-z][A-Za-z0-9\-\s']{2,60}?)"
    r"(?=[.,!?]|\sso\b|\sand\b|\sbecause\b|\swhich\b|\sthat\b|$)",
    re.IGNORECASE,
)

ETHICAL_GUARDRAILS = """You are an interview coach for under-resourced students.
Hard rules you must follow at all times:
- Do NOT judge accent, dialect, identity, personality, socioeconomic background, or cultural style.
- Do NOT invent achievements the user did not mention.
- Do NOT predict whether the user will or will not get the role.
- Do NOT encourage lying, exaggeration, or fabricating credentials.
- Focus only on clarity, structure, specificity, reflection, and alignment with the opportunity.
- For technical questions, be honest about uncertainty in your scoring; you may make math or factual mistakes.
- Be encouraging but honest. Treat the user as capable.
"""

SAMPLES = {
    "first_internship": {
        "label": "First Internship Interview",
        "interview_type": "Internship",
        "interview_mode": "Qualitative",
        "difficulty": "Beginner",
        "question_count": 3,
        "timer_seconds": None,
        "opportunity_description": (
            "Summer software engineering internship for early-career students. "
            "Looking for curious learners who can pick up new tools quickly and "
            "communicate clearly with a team."
        ),
        "applicant_background": (
            "I am a community college student transferring next year. I have "
            "built a couple of personal projects but I have never worked at a "
            "real software company, and nobody in my family has either."
        ),
    },
    "research_assistant": {
        "label": "Research Assistant Interview",
        "interview_type": "Research Program",
        "interview_mode": "Mixed",
        "difficulty": "Intermediate",
        "question_count": 3,
        "timer_seconds": 90,
        "opportunity_description": (
            "Summer research assistant role for early undergraduates interested "
            "in scientific computing, data analysis, and physical modeling. "
            "Applicants should be curious, persistent, comfortable learning new "
            "tools, and able to explain technical ideas clearly."
        ),
        "applicant_background": (
            "I am a first-year student interested in physics and computer "
            "science. I built a Monte Carlo option pricing project and a Gaia "
            "star-mapping visualization. I come from a school where few "
            "students had access to research or technical internships, so I am "
            "still learning how to talk about my experience professionally."
        ),
    },
    "scholarship": {
        "label": "Scholarship Interview",
        "interview_type": "Scholarship",
        "interview_mode": "Qualitative",
        "difficulty": "Intermediate",
        "question_count": 3,
        "timer_seconds": None,
        "opportunity_description": (
            "Need-based scholarship that supports first-generation college "
            "students pursuing STEM. Reviewers care about resilience, clarity "
            "of purpose, and what the funding would actually unlock."
        ),
        "applicant_background": (
            "I am a first-generation college student from a rural town. I work "
            "part-time to help with bills. Without this scholarship I would "
            "have to keep working enough hours that my coursework would suffer."
        ),
    },
}


def has_api_key() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())


def model_name() -> str:
    return os.environ.get("ANTHROPIC_MODEL", "").strip() or DEFAULT_ANTHROPIC_MODEL
