"""InterviewOS - A practice environment for high-stakes interviews.

Built for first-gen, low-income, rural, community college, immigrant, and
otherwise under-resourced students who do not have alumni networks,
recruiters, or family connections to run realistic mock interviews.

This is a single-file Streamlit app. No database, no auth, no file upload.
"""

from __future__ import annotations

import json
import os
import re
import time
from typing import Any

import streamlit as st
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError

load_dotenv()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

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
    "clarity", "specificity", "confidence", "relevance",
    "authenticity", "structure", "evidence_examples", "growth_mindset",
]
TECHNICAL_RUBRIC_KEYS = ["technical_reasoning", "technical_correctness"]

# Hedging words we strip in the improved-answer rewrite and count for the
# Confidence rubric. Kept short on purpose so we don't flatten anyone's voice.
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


# ---------------------------------------------------------------------------
# Pydantic schemas (validate Claude / mock JSON outputs)
# ---------------------------------------------------------------------------


class QuestionChoice(BaseModel):
    label: str
    text: str


class Question(BaseModel):
    question_text: str
    question_type: str = "qualitative"  # 'qualitative' or 'technical'
    answer_format: str = "free_response"  # or 'multiple_choice_with_explanation'
    choices: list[QuestionChoice] = Field(default_factory=list)
    latex: str | None = None
    interviewer_note: str = ""


class Answer(BaseModel):
    selected_choice: str | None = None
    written_response: str = ""


class InterviewPlan(BaseModel):
    resolved_mode: str
    resolved_difficulty: str
    resolved_question_count: int = Field(ge=1, le=MAX_QUESTION_COUNT)
    resolved_timer_seconds: int | None = None
    rationale: str = ""
    question_style_notes: str = ""


class RubricItem(BaseModel):
    score: int = Field(ge=1, le=5)
    feedback: str


class QuestionReview(BaseModel):
    question_index: int
    question_type: str
    what_went_well: str
    what_to_improve: str
    correct_answer_if_applicable: str | None = None
    explanation_if_applicable: str | None = None


class ImprovedAnswer(BaseModel):
    original_question: str
    rewrite: str
    what_changed: str


class TargetedDrill(BaseModel):
    drill: str
    why_this_helps: str


class Feedback(BaseModel):
    overall_score: int = Field(ge=0, le=100)
    overall_summary: str
    rubric: dict[str, RubricItem]
    question_reviews: list[QuestionReview] = Field(default_factory=list)
    strongest_moment: str
    biggest_issue: str
    improved_answer: ImprovedAnswer
    targeted_drills: list[TargetedDrill]
    next_practice_question: str
    ethical_reminder: str


# `from __future__ import annotations` defers annotation evaluation, so we
# explicitly rebuild the models that hold forward references.
QuestionChoice.model_rebuild()
Question.model_rebuild()
Answer.model_rebuild()
InterviewPlan.model_rebuild()
RubricItem.model_rebuild()
QuestionReview.model_rebuild()
ImprovedAnswer.model_rebuild()
TargetedDrill.model_rebuild()
Feedback.model_rebuild()


# ---------------------------------------------------------------------------
# API key + Claude helpers
# ---------------------------------------------------------------------------


def has_api_key() -> bool:
    """Return True if an Anthropic API key is configured."""
    return bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())


def _model_name() -> str:
    return os.environ.get("ANTHROPIC_MODEL", "").strip() or DEFAULT_ANTHROPIC_MODEL


def _extract_json(text: str) -> dict[str, Any]:
    """Best-effort JSON extraction from a model response."""
    text = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise


def call_claude_json(system_prompt: str, user_prompt: str) -> dict[str, Any]:
    """Call Claude and parse the response as JSON.

    Raises on failure so callers can fall back to mock data.
    """
    from anthropic import Anthropic  # imported lazily

    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    message = client.messages.create(
        model=_model_name(),
        max_tokens=2500,
        system=(
            system_prompt
            + "\n\nReturn ONLY a single valid JSON object. No prose. No markdown. No code fences."
        ),
        messages=[{"role": "user", "content": user_prompt}],
    )
    text_parts = [
        block.text for block in message.content if getattr(block, "type", "") == "text"
    ]
    raw = "".join(text_parts).strip()
    return _extract_json(raw)


# ---------------------------------------------------------------------------
# Transcript-shape adapters
#
# A transcript turn is `{"question": <Question dict>, "answer": <Answer dict>}`
# but older code (and any leftover Claude outputs) may pass plain strings.
# These helpers smooth over both shapes so the rest of the code is simple.
# ---------------------------------------------------------------------------


def _question_obj(turn: dict) -> dict:
    q = turn.get("question")
    if isinstance(q, str):
        return {
            "question_text": q,
            "question_type": "qualitative",
            "answer_format": "free_response",
            "choices": [],
            "latex": None,
            "interviewer_note": "",
        }
    return q or {}


def _question_text(turn: dict) -> str:
    q = turn.get("question")
    if isinstance(q, str):
        return q
    return (q or {}).get("question_text", "")


def _answer_text(turn: dict) -> str:
    a = turn.get("answer")
    if isinstance(a, str):
        return a
    return (a or {}).get("written_response", "")


def _selected_choice(turn: dict) -> str | None:
    a = turn.get("answer")
    if isinstance(a, str):
        return None
    return (a or {}).get("selected_choice")


def _question_type(turn: dict) -> str:
    return _question_obj(turn).get("question_type", "qualitative")


# ---------------------------------------------------------------------------
# Mock mode: technical question banks
#
# Each entry carries the full structured Question fields plus private
# `_correct_label` and `_correct_explanation` used only during mock scoring.
# We strip those private fields before showing the question to the user.
# ---------------------------------------------------------------------------


TECHNICAL_QUESTION_BANK: dict[str, list[dict]] = {
    "Scientific Computing": [
        {
            "question_text": (
                "In a Monte Carlo simulation estimating an option price, what "
                "generally happens to the standard error as the number of "
                "independent simulated paths N increases?"
            ),
            "latex": r"SE \propto \frac{1}{\sqrt{N}}",
            "choices": [
                {"label": "A", "text": "It usually decreases proportional to 1 / sqrt(N)."},
                {"label": "B", "text": "It usually decreases proportional to 1 / N^2."},
                {"label": "C", "text": "It usually increases proportional to sqrt(N)."},
                {"label": "D", "text": "It does not depend on N."},
            ],
            "interviewer_note": "Probing numerical convergence intuition.",
            "_correct_label": "A",
            "_correct_explanation": (
                "Standard error of a sample mean from i.i.d. draws scales as "
                "sigma / sqrt(N). To halve the error you need 4x the paths."
            ),
        },
        {
            "question_text": (
                "You compute (0.1 + 0.2) in IEEE 754 double precision and "
                "compare to 0.3 with ==. Which best describes what happens?"
            ),
            "latex": None,
            "choices": [
                {"label": "A", "text": "It returns True; floating point handles this exactly."},
                {"label": "B", "text": "It returns False because 0.1 and 0.2 are not exactly representable in binary."},
                {"label": "C", "text": "It raises a runtime error."},
                {"label": "D", "text": "It depends on whether you use float32 or float64."},
            ],
            "interviewer_note": "Checking floating point literacy.",
            "_correct_label": "B",
            "_correct_explanation": (
                "0.1 and 0.2 cannot be represented exactly in binary floating "
                "point, so their sum has a tiny rounding error and is not "
                "bit-equal to 0.3. Use math.isclose() or a tolerance instead."
            ),
        },
        {
            "question_text": (
                "You are integrating an ODE with forward Euler and your "
                "solution blows up. Which change is most likely to help first?"
            ),
            "latex": None,
            "choices": [
                {"label": "A", "text": "Use a larger time step so you take fewer steps overall."},
                {"label": "B", "text": "Reduce the time step until the scheme is stable for your problem."},
                {"label": "C", "text": "Switch from float64 to float32 to save memory."},
                {"label": "D", "text": "Add more random noise to regularize the solution."},
            ],
            "interviewer_note": "Probing numerical stability intuition.",
            "_correct_label": "B",
            "_correct_explanation": (
                "Forward Euler is only conditionally stable. Shrinking the "
                "time step until you are below the stability bound is the "
                "first practical fix; longer-term, switch to an implicit "
                "scheme."
            ),
        },
        {
            "question_text": (
                "You have a 1000x500 matrix A and a length-500 vector x. "
                "What is the shape of A @ x?"
            ),
            "latex": r"A \in \mathbb{R}^{1000 \times 500}, \; x \in \mathbb{R}^{500}",
            "choices": [
                {"label": "A", "text": "Length 1000."},
                {"label": "B", "text": "Length 500."},
                {"label": "C", "text": "1000 x 500 (same as A)."},
                {"label": "D", "text": "Scalar."},
            ],
            "interviewer_note": "Quick linear algebra dimension check.",
            "_correct_label": "A",
            "_correct_explanation": (
                "Matrix-vector product (m x n) @ (n,) -> (m,). So 1000x500 "
                "times length-500 yields length-1000."
            ),
        },
    ],
    "Quant / Trading": [
        {
            "question_text": (
                "You roll a fair six-sided die once. You win the dollar "
                "amount shown. What is the expected value of the game?"
            ),
            "latex": r"E[X] = \sum_{k=1}^{6} k \cdot \tfrac{1}{6}",
            "choices": [
                {"label": "A", "text": "$3.00"},
                {"label": "B", "text": "$3.50"},
                {"label": "C", "text": "$4.00"},
                {"label": "D", "text": "$6.00"},
            ],
            "interviewer_note": "Warm-up expected value.",
            "_correct_label": "B",
            "_correct_explanation": (
                "(1+2+3+4+5+6)/6 = 21/6 = 3.50. Memorize this — it's the "
                "starting point for many quant warmups."
            ),
        },
        {
            "question_text": (
                "X and Y are independent random variables, each with "
                "variance sigma^2. What is Var(X + Y)?"
            ),
            "latex": r"\mathrm{Var}(X + Y) = \mathrm{Var}(X) + \mathrm{Var}(Y) + 2\,\mathrm{Cov}(X, Y)",
            "choices": [
                {"label": "A", "text": "sigma^2"},
                {"label": "B", "text": "2 * sigma"},
                {"label": "C", "text": "2 * sigma^2"},
                {"label": "D", "text": "4 * sigma^2"},
            ],
            "interviewer_note": "Variance of independent sum.",
            "_correct_label": "C",
            "_correct_explanation": (
                "For independent X and Y, Cov(X, Y) = 0 so Var(X+Y) = "
                "Var(X) + Var(Y) = 2 sigma^2. Standard deviation is "
                "sigma * sqrt(2), not 2 sigma."
            ),
        },
        {
            "question_text": (
                "You flip a fair coin until you get heads. What is the "
                "expected number of total flips (including the heads)?"
            ),
            "latex": r"E[N] = \sum_{k=1}^{\infty} k \cdot (1/2)^k",
            "choices": [
                {"label": "A", "text": "1"},
                {"label": "B", "text": "1.5"},
                {"label": "C", "text": "2"},
                {"label": "D", "text": "Infinity"},
            ],
            "interviewer_note": "Geometric distribution mean.",
            "_correct_label": "C",
            "_correct_explanation": (
                "Geometric distribution with p = 1/2 has mean 1/p = 2. "
                "Quick sanity check: half the time you stop in 1 flip, the "
                "other half you average 1 + (mean again), giving E = 0.5 + "
                "0.5*(1+E), so E = 2."
            ),
        },
        {
            "question_text": (
                "Two strategies have the same expected daily return, but "
                "Strategy A has half the daily volatility of Strategy B. "
                "All else equal, which has the better Sharpe ratio?"
            ),
            "latex": r"\text{Sharpe} = \frac{E[R] - R_f}{\sigma}",
            "choices": [
                {"label": "A", "text": "Strategy A — same return per unit risk is doubled."},
                {"label": "B", "text": "Strategy B — higher volatility means more upside."},
                {"label": "C", "text": "They are equal because expected return is the same."},
                {"label": "D", "text": "Cannot tell without knowing the risk-free rate."},
            ],
            "interviewer_note": "Sharpe intuition.",
            "_correct_label": "A",
            "_correct_explanation": (
                "Sharpe = (mean - rf) / sigma. Halving sigma at the same mean "
                "roughly doubles Sharpe (assuming rf is small or comparable). "
                "Lower vol at the same expected return is essentially always "
                "preferred."
            ),
        },
    ],
    "Technical SWE": [
        {
            "question_text": (
                "What is the average-case time complexity of binary search "
                "on a sorted array of length n?"
            ),
            "latex": r"O(\log n)",
            "choices": [
                {"label": "A", "text": "O(1)"},
                {"label": "B", "text": "O(log n)"},
                {"label": "C", "text": "O(n)"},
                {"label": "D", "text": "O(n log n)"},
            ],
            "interviewer_note": "Classic complexity warmup.",
            "_correct_label": "B",
            "_correct_explanation": (
                "Each step halves the search space, so the number of steps "
                "grows as log2(n). Worst case is also O(log n)."
            ),
        },
        {
            "question_text": (
                "You need to find the shortest path (fewest edges) from a "
                "node in an unweighted graph. Which traversal is best?"
            ),
            "latex": None,
            "choices": [
                {"label": "A", "text": "DFS, because it explores deep first."},
                {"label": "B", "text": "BFS, because it visits nodes in order of distance."},
                {"label": "C", "text": "Either — they give the same path on unweighted graphs."},
                {"label": "D", "text": "Dijkstra is required for shortest paths."},
            ],
            "interviewer_note": "Graph traversal selection.",
            "_correct_label": "B",
            "_correct_explanation": (
                "BFS visits nodes in increasing distance from the start, so "
                "the first time you reach the target is via the fewest edges. "
                "Dijkstra is for weighted graphs."
            ),
        },
        {
            "question_text": (
                "What is the average-case lookup time of a well-implemented "
                "hash map?"
            ),
            "latex": None,
            "choices": [
                {"label": "A", "text": "O(1) on average."},
                {"label": "B", "text": "O(log n)."},
                {"label": "C", "text": "O(n)."},
                {"label": "D", "text": "O(n log n)."},
            ],
            "interviewer_note": "Hash map basics.",
            "_correct_label": "A",
            "_correct_explanation": (
                "With a good hash function and sensible load factor, hash "
                "map lookup is amortized O(1). Worst case can degrade to "
                "O(n) with adversarial inputs or poor hashing."
            ),
        },
        {
            "question_text": (
                "You're processing a stream and need 'last in, first out' "
                "semantics. Which data structure fits?"
            ),
            "latex": None,
            "choices": [
                {"label": "A", "text": "Queue."},
                {"label": "B", "text": "Stack."},
                {"label": "C", "text": "Priority queue."},
                {"label": "D", "text": "Linked list with random access."},
            ],
            "interviewer_note": "LIFO vs FIFO recall.",
            "_correct_label": "B",
            "_correct_explanation": (
                "LIFO = Last In First Out = stack. Queue is FIFO."
            ),
        },
    ],
    "Data Science": [
        {
            "question_text": (
                "Your model gets 99% accuracy on the training set and 60% "
                "on a held-out test set. What is the most likely problem?"
            ),
            "latex": None,
            "choices": [
                {"label": "A", "text": "The model is underfitting; it needs more capacity."},
                {"label": "B", "text": "The model is overfitting to the training data."},
                {"label": "C", "text": "The test set is too small to be meaningful."},
                {"label": "D", "text": "The features are too informative."},
            ],
            "interviewer_note": "Overfitting symptom.",
            "_correct_label": "B",
            "_correct_explanation": (
                "Large gap between train and test performance is the "
                "textbook overfitting signal. Try regularization, simpler "
                "models, more data, or early stopping."
            ),
        },
        {
            "question_text": (
                "You are classifying fraud where 1% of transactions are "
                "fraudulent. A model that predicts 'not fraud' for every "
                "transaction has what accuracy?"
            ),
            "latex": None,
            "choices": [
                {"label": "A", "text": "Around 1%."},
                {"label": "B", "text": "Around 50%."},
                {"label": "C", "text": "Around 99%."},
                {"label": "D", "text": "Cannot tell without more information."},
            ],
            "interviewer_note": "Class imbalance trap.",
            "_correct_label": "C",
            "_correct_explanation": (
                "If 99% of transactions are not fraud, predicting 'not "
                "fraud' for every one gives 99% accuracy — and is useless. "
                "This is why precision/recall and F1 matter for imbalanced "
                "problems."
            ),
        },
        {
            "question_text": (
                "Why do we hold out a test set instead of evaluating on "
                "training data?"
            ),
            "latex": None,
            "choices": [
                {"label": "A", "text": "Training data is too large to evaluate quickly."},
                {"label": "B", "text": "To estimate how the model will perform on data it has not seen."},
                {"label": "C", "text": "Test data is more accurate than training data."},
                {"label": "D", "text": "It is required by law for production models."},
            ],
            "interviewer_note": "Generalization intuition.",
            "_correct_label": "B",
            "_correct_explanation": (
                "The whole point is to estimate generalization — performance "
                "on data the model has never been fit on. Training accuracy "
                "alone tells you almost nothing about real-world behavior."
            ),
        },
        {
            "question_text": (
                "Which statement best captures the bias-variance tradeoff?"
            ),
            "latex": r"\text{Error} \approx \text{Bias}^2 + \text{Variance} + \text{Noise}",
            "choices": [
                {"label": "A", "text": "Lower bias always means lower test error."},
                {"label": "B", "text": "Reducing model complexity usually lowers variance but can raise bias."},
                {"label": "C", "text": "Variance is the part of error you cannot reduce."},
                {"label": "D", "text": "Bias and variance are independent of model choice."},
            ],
            "interviewer_note": "Bias-variance literacy.",
            "_correct_label": "B",
            "_correct_explanation": (
                "Simpler models tend to have lower variance (more stable "
                "across resamples) but higher bias (less flexible). Test "
                "error is roughly bias^2 + variance + irreducible noise."
            ),
        },
    ],
}

# Fallback bank for interview types that have no dedicated technical bank.
_DEFAULT_TECHNICAL_FALLBACK = "Technical SWE"


# ---------------------------------------------------------------------------
# Mock mode: qualitative starters and adaptive follow-ups
# ---------------------------------------------------------------------------


QUALITATIVE_STARTERS = {
    "Internship": (
        "Walk me through what drew you to this internship and what you "
        "hope to learn during the summer."
    ),
    "Scholarship": (
        "Tell me about yourself and what this scholarship would make "
        "possible for you."
    ),
    "Research Program": (
        "Tell me a little about your background and a project or idea "
        "that genuinely excites you."
    ),
    "College / Transfer": (
        "Why this school, and what do you hope your next two years look "
        "like academically?"
    ),
    "First Job": (
        "Walk me through your background and why this role caught your "
        "attention."
    ),
    "Technical SWE": (
        "Walk me through a project you actually built and why you chose "
        "the design you did."
    ),
    "Quant / Trading": (
        "Tell me about a problem — quantitative or otherwise — where you "
        "had to reason from first principles, not memorized formulas."
    ),
    "Scientific Computing": (
        "Tell me about a computational project you worked on and one "
        "thing about it that surprised you."
    ),
    "Data Science": (
        "Walk me through a data project you actually finished, and what "
        "you would do differently next time."
    ),
    "Custom": (
        "Tell me a little about yourself and why this opportunity caught "
        "your attention."
    ),
}


def _opportunity_label(config: dict) -> str:
    return config.get("opportunity_description", "").strip() or config["interview_type"]


def _diagnose_answer(answer: str) -> str:
    """Categorize the previous answer to pick a follow-up style."""
    text = (answer or "").strip()
    words = text.split()
    if len(words) < 12:
        return "vague"
    if not re.search(r"\d|project|built|wrote|made|led|won|class|course|lab", text, re.I):
        return "no_evidence"
    if not re.search(r"because|so that|in order to|matters|care|excited|interested", text, re.I):
        return "no_motivation"
    if len(words) > 70:
        return "strong"
    return "ok"


def _make_qualitative_starter(config: dict) -> dict:
    """Return a structured opening qualitative Question dict."""
    text = QUALITATIVE_STARTERS.get(
        config["interview_type"], QUALITATIVE_STARTERS["Internship"]
    )
    return {
        "question_text": text,
        "question_type": "qualitative",
        "answer_format": "free_response",
        "choices": [],
        "latex": None,
        "interviewer_note": "Opening question.",
    }


def _make_qualitative_followup(config: dict, transcript: list[dict]) -> dict:
    """Return a structured adaptive qualitative Question dict."""
    last_answer = _answer_text(transcript[-1]) if transcript else ""
    diagnosis = _diagnose_answer(last_answer)
    opportunity = _opportunity_label(config).strip().rstrip(".!?,;:").lower()
    opportunity_short = (
        opportunity[:60].rsplit(" ", 1)[0] if len(opportunity) > 60 else opportunity
    )

    follow_ups = {
        "vague": (
            "Can you give me one concrete example? Pick a specific moment "
            "— a project, a class, a conversation — and walk me through "
            "what you actually did.",
            "Pushing for a concrete example.",
        ),
        "no_evidence": (
            "What is one thing you have actually built, written, or led "
            "that shows what you just described? Tell me what you did "
            "and what the result was.",
            "Asking for evidence behind the claim.",
        ),
        "no_motivation": (
            f"Why does this opportunity ({opportunity_short}) matter to "
            "you personally? What would change for you if you got it?",
            "Probing motivation and stakes.",
        ),
        "strong": (
            "That is a strong start. What is the hardest thing you ran "
            "into in that work, and what did you learn from it?",
            "Going deeper on a strong answer.",
        ),
        "ok": (
            "Tell me about a time you had to learn something new quickly. "
            "What did you do, and what would you do differently next time?",
            "Standard follow-up on learning ability.",
        ),
    }
    text, note = follow_ups[diagnosis]
    return {
        "question_text": text,
        "question_type": "qualitative",
        "answer_format": "free_response",
        "choices": [],
        "latex": None,
        "interviewer_note": note,
    }


def _bank_for(interview_type: str) -> list[dict]:
    if interview_type in TECHNICAL_QUESTION_BANK:
        return TECHNICAL_QUESTION_BANK[interview_type]
    if interview_type == "Research Program":
        return TECHNICAL_QUESTION_BANK["Scientific Computing"]
    return TECHNICAL_QUESTION_BANK[_DEFAULT_TECHNICAL_FALLBACK]


def _public_question(bank_item: dict) -> dict:
    """Strip the private answer-key fields before showing to the user.

    The full bank item (with `_correct_label` and `_correct_explanation`) is
    stored in the transcript so mock_feedback can score correctness; the
    public-facing render code only ever sees the public fields.
    """
    return {
        "question_text": bank_item["question_text"],
        "question_type": "technical",
        "answer_format": "multiple_choice_with_explanation",
        "choices": list(bank_item.get("choices", [])),
        "latex": bank_item.get("latex"),
        "interviewer_note": bank_item.get("interviewer_note", ""),
        # Carry the answer key forward as private metadata so mock scoring
        # can use it. Fields prefixed with `_` are stripped from any prompt
        # we send to Claude (see _transcript_block).
        "_correct_label": bank_item.get("_correct_label"),
        "_correct_explanation": bank_item.get("_correct_explanation"),
    }


def _pick_technical_question(config: dict, transcript: list[dict]) -> dict:
    """Pick a technical question from the bank, avoiding duplicates."""
    bank = _bank_for(config["interview_type"])
    used_texts = {_question_text(t) for t in transcript}
    for item in bank:
        if item["question_text"] not in used_texts:
            return _public_question(item)
    return _public_question(bank[0])


# ---------------------------------------------------------------------------
# Mock mode: planning + question dispatch
# ---------------------------------------------------------------------------


def _question_types_for_plan(mode: str, n: int) -> list[str]:
    """Pick the type of each question in the interview given mode + count."""
    if mode == "Qualitative":
        return ["qualitative"] * n
    if mode == "Technical":
        return ["technical"] * n
    # Mixed: lead with qualitative, alternate.
    fixed = {
        3: ["qualitative", "technical", "qualitative"],
        5: ["qualitative", "technical", "qualitative", "technical", "qualitative"],
        7: [
            "qualitative", "technical", "qualitative", "technical",
            "qualitative", "technical", "qualitative",
        ],
        10: [
            "qualitative", "technical", "qualitative", "technical", "qualitative",
            "technical", "qualitative", "technical", "qualitative", "technical",
        ],
    }
    if n in fixed:
        return fixed[n]
    return ["qualitative" if i % 2 == 0 else "technical" for i in range(n)]


def mock_plan_interview(config: dict) -> dict:
    """Heuristic interview planner used when no API key is configured."""
    user_mode = config.get("interview_mode", "Auto")
    user_diff = config.get("difficulty", "Auto")
    user_n = config.get("question_count")
    user_timer = config.get("timer_seconds")
    interview_type = config.get("interview_type", "Internship")
    opp = (config.get("opportunity_description") or "").lower()
    bg = (config.get("applicant_background") or "").lower()
    full = f"{opp} {bg}"

    explicitly_technical = interview_type in {
        "Technical SWE", "Quant / Trading", "Scientific Computing", "Data Science",
    }

    if user_mode and user_mode != "Auto":
        resolved_mode = user_mode
    elif explicitly_technical:
        resolved_mode = "Mixed"
    else:
        tech_kw = {
            "code", "algorithm", "data structure", "model", "modeling",
            "research", "compute", "ml", "machine learning", "statistics",
            "python", "scientific", "math", "quantitative",
        }
        resolved_mode = "Mixed" if any(k in full for k in tech_kw) else "Qualitative"

    if user_diff and user_diff != "Auto":
        resolved_difficulty = user_diff
    elif any(k in full for k in ["beginner", "first", "early", "no experience", "new to"]):
        resolved_difficulty = "Beginner"
    elif any(k in full for k in ["expert", "advanced", "phd", "senior", "graduate"]):
        resolved_difficulty = "Advanced"
    else:
        resolved_difficulty = "Intermediate"

    resolved_n = user_n if isinstance(user_n, int) and user_n > 0 else DEFAULT_QUESTION_COUNT
    resolved_n = max(1, min(MAX_QUESTION_COUNT, resolved_n))

    resolved_timer = user_timer if isinstance(user_timer, int) and user_timer > 0 else None

    why_mode = (
        f"the {interview_type} interview type"
        if explicitly_technical
        else "the description you provided"
        if (opp or bg)
        else "a sensible default"
    )
    rationale = (
        f"Auto-planned a {resolved_mode.lower()} interview at "
        f"{resolved_difficulty.lower()} difficulty, {resolved_n} questions"
        + (f", {resolved_timer}s timer per question" if resolved_timer else ", no timer")
        + f", based on {why_mode}."
    )
    style_notes = (
        "Mix concrete examples with conceptual reasoning. Adapt to the "
        "user's previous answer. For technical questions, write four "
        "labeled choices and ask the user to explain their reasoning."
    )
    return {
        "resolved_mode": resolved_mode,
        "resolved_difficulty": resolved_difficulty,
        "resolved_question_count": resolved_n,
        "resolved_timer_seconds": resolved_timer,
        "rationale": rationale,
        "question_style_notes": style_notes,
    }


def plan_interview(config: dict) -> dict:
    """Build the resolved interview plan, calling Claude if available."""
    if not has_api_key():
        plan = mock_plan_interview(config)
    else:
        system = (
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
            "- For Technical SWE, Quant / Trading, Scientific Computing, or "
            "Data Science, prefer Mixed unless told otherwise.\n"
            "- Avoid more than 10 questions for a hackathon demo."
        )
        user = (
            "User selections (Auto means infer):\n"
            f"- Interview mode: {config.get('interview_mode', 'Auto')}\n"
            f"- Difficulty: {config.get('difficulty', 'Auto')}\n"
            f"- Question count: {config.get('question_count') or 'Auto'}\n"
            f"- Timer (seconds/question): {config.get('timer_seconds') or 'Off'}\n"
            f"- Interview type: {config.get('interview_type')}\n"
            f"- Opportunity description: "
            f"{(config.get('opportunity_description') or '(none)').strip()}\n"
            f"- Applicant background: "
            f"{(config.get('applicant_background') or '(none)').strip()}\n\n"
            'Return JSON with keys: resolved_mode, resolved_difficulty, '
            "resolved_question_count, resolved_timer_seconds, rationale, "
            "question_style_notes."
        )
        try:
            data = call_claude_json(system, user)
            validated = InterviewPlan(**data)
            plan = validated.model_dump()
        except (ValidationError, Exception):  # noqa: BLE001
            plan = mock_plan_interview(config)

    plan["question_types"] = _question_types_for_plan(
        plan["resolved_mode"], plan["resolved_question_count"]
    )
    return plan


def mock_start_question(config: dict, plan: dict) -> dict:
    """Return the structured opening Question dict respecting the plan."""
    types = plan.get("question_types") or _question_types_for_plan(
        plan["resolved_mode"], plan["resolved_question_count"]
    )
    if types and types[0] == "technical":
        return _pick_technical_question(config, [])
    return _make_qualitative_starter(config)


def mock_next_question(config: dict, plan: dict, transcript: list[dict]) -> dict:
    """Return the structured next Question dict, or empty if the interview is done."""
    types = plan.get("question_types") or _question_types_for_plan(
        plan["resolved_mode"], plan["resolved_question_count"]
    )
    n = int(plan["resolved_question_count"])
    idx = len(transcript)
    if idx >= n:
        return {
            "question_text": "",
            "question_type": "qualitative",
            "answer_format": "free_response",
            "choices": [],
            "latex": None,
            "interviewer_note": "Interview complete. Ready to score.",
        }
    next_type = types[idx] if idx < len(types) else "qualitative"
    if next_type == "technical":
        return _pick_technical_question(config, transcript)
    return _make_qualitative_followup(config, transcript)


# ---------------------------------------------------------------------------
# Real-mode prompt construction
# ---------------------------------------------------------------------------


def _config_block(config: dict) -> str:
    return (
        f"Interview type: {config['interview_type']}\n"
        f"Opportunity description: {config.get('opportunity_description', '').strip() or '(none provided)'}\n"
        f"Applicant background: {config.get('applicant_background', '').strip() or '(none provided)'}"
    )


def _plan_block(plan: dict) -> str:
    timer = plan.get("resolved_timer_seconds")
    timer_str = f"{timer}s/question" if timer else "no timer"
    return (
        f"Resolved plan: {plan['resolved_mode']} mode, "
        f"{plan['resolved_difficulty']} difficulty, "
        f"{plan['resolved_question_count']} questions, {timer_str}.\n"
        f"Question style notes: {plan.get('question_style_notes', '')}"
    )


def _transcript_block(transcript: list[dict]) -> str:
    """Format the transcript for prompt inclusion. Strips private answer-key fields."""
    if not transcript:
        return "(no answers yet)"
    lines = []
    for i, turn in enumerate(transcript, start=1):
        q = _question_obj(turn)
        qt = q.get("question_text", "")
        qtype = q.get("question_type", "qualitative")
        choices_text = ""
        if q.get("answer_format") == "multiple_choice_with_explanation" and q.get("choices"):
            choices_text = "\n  Choices:\n" + "\n".join(
                f"    {c['label']}. {c['text']}" for c in q["choices"]
            )
        sel = _selected_choice(turn)
        ans_text = _answer_text(turn)
        sel_str = f"\n  Selected: {sel}" if sel else ""
        lines.append(
            f"Q{i} ({qtype}): {qt}{choices_text}\n"
            f"A{i}:{sel_str}\n  Written: {ans_text}"
        )
    return "\n\n".join(lines)


def _question_schema_instructions() -> str:
    return (
        "Return ONLY a JSON object matching this schema:\n"
        "{\n"
        '  "question_text": string,\n'
        '  "question_type": "qualitative" | "technical",\n'
        '  "answer_format": "free_response" | "multiple_choice_with_explanation",\n'
        '  "choices": [{"label": "A"|"B"|"C"|"D", "text": string}],\n'
        '  "latex": string | null,\n'
        '  "interviewer_note": string\n'
        "}\n"
        "Rules:\n"
        "- For qualitative questions: answer_format is 'free_response' and choices is [].\n"
        "- For technical questions: answer_format is "
        "'multiple_choice_with_explanation' and choices has EXACTLY 4 items "
        "labeled A, B, C, D.\n"
        "- Do NOT include the correct answer or any answer-key field.\n"
        "- For math, include a LaTeX string in 'latex' (no surrounding $$). "
        "Otherwise set latex to null.\n"
        "- Keep question_text concise and conversational (1-3 sentences).\n"
        "- 'interviewer_note' is a short backstage line about why you are "
        "asking this (shown to the user as 'Coach: ...')."
    )


def _coerce_question(data: dict, desired_type: str) -> dict:
    """Make a Claude response well-formed enough to validate."""
    out = dict(data)
    qtype = out.get("question_type") or desired_type
    out["question_type"] = qtype if qtype in {"qualitative", "technical"} else desired_type
    fmt = out.get("answer_format")
    if out["question_type"] == "qualitative":
        out["answer_format"] = "free_response"
        out["choices"] = []
    else:
        if fmt != "multiple_choice_with_explanation":
            out["answer_format"] = "multiple_choice_with_explanation"
        choices = out.get("choices") or []
        cleaned = []
        for c in choices[:4]:
            if isinstance(c, dict) and "label" in c and "text" in c:
                cleaned.append({"label": str(c["label"]).strip(), "text": str(c["text"])})
        if len(cleaned) != 4:
            # Reject malformed choice list — caller will fall back to mock.
            raise ValueError("technical question must have exactly 4 choices")
        out["choices"] = cleaned
    out.setdefault("latex", None)
    out.setdefault("interviewer_note", "")
    return out


def start_interview(config: dict, plan: dict) -> dict:
    """Generate the first interview question (structured Question dict)."""
    types = plan.get("question_types") or _question_types_for_plan(
        plan["resolved_mode"], plan["resolved_question_count"]
    )
    desired_type = types[0] if types else "qualitative"

    if not has_api_key():
        return mock_start_question(config, plan)

    system = (
        ETHICAL_GUARDRAILS
        + "\nYou are starting a mock interview.\n"
        + _question_schema_instructions()
    )
    user = (
        f"This is the OPENING question (question 1 of "
        f"{plan['resolved_question_count']}).\n"
        f"{_config_block(config)}\n"
        f"{_plan_block(plan)}\n"
        f"Generate a {desired_type.upper()} opening question now."
    )
    try:
        data = call_claude_json(system, user)
        data = _coerce_question(data, desired_type)
        validated = Question(**data)
        return validated.model_dump()
    except (ValidationError, Exception):  # noqa: BLE001
        return mock_start_question(config, plan)


def next_question(config: dict, plan: dict, transcript: list[dict]) -> dict:
    """Generate the next interview question, adapting to the transcript."""
    n = int(plan["resolved_question_count"])
    idx = len(transcript)
    if idx >= n:
        return {
            "question_text": "",
            "question_type": "qualitative",
            "answer_format": "free_response",
            "choices": [],
            "latex": None,
            "interviewer_note": "Interview complete.",
        }

    types = plan.get("question_types") or _question_types_for_plan(
        plan["resolved_mode"], n
    )
    desired_type = types[idx] if idx < len(types) else "qualitative"

    if not has_api_key():
        return mock_next_question(config, plan, transcript)

    system = (
        ETHICAL_GUARDRAILS
        + "\nYou are mid-interview. Adapt to the user's previous answer:\n"
        "- If vague: ask for a concrete example.\n"
        "- If lacks motivation: ask why this opportunity matters.\n"
        "- If a claim has no evidence: ask for evidence.\n"
        "- If strong: ask a deeper follow-up.\n"
        "- If they did not answer the question: redirect politely.\n"
        + _question_schema_instructions()
    )
    user = (
        f"Question {idx + 1} of {n}. Generate a "
        f"{desired_type.upper()} question.\n"
        f"{_config_block(config)}\n"
        f"{_plan_block(plan)}\n\n"
        f"Transcript so far:\n{_transcript_block(transcript)}"
    )
    try:
        data = call_claude_json(system, user)
        data = _coerce_question(data, desired_type)
        validated = Question(**data)
        return validated.model_dump()
    except (ValidationError, Exception):  # noqa: BLE001
        return mock_next_question(config, plan, transcript)


# ---------------------------------------------------------------------------
# Mock mode: scoring (rubric, drills, rewrite, question reviews)
# ---------------------------------------------------------------------------


def _strip_hedges(text: str) -> str:
    """Remove hedging words and clean up the spacing/punctuation left behind."""
    out = text
    prev = None
    while out != prev:
        prev = out
        out = HEDGE_PATTERN.sub("", out)
        out = re.sub(r"\s{2,}", " ", out)
    out = re.sub(r"\s+([,.!?;:])", r"\1", out)
    out = re.sub(r"^\s*[,.;:]\s*", "", out)
    out = re.sub(r",\s*,", ",", out)
    out = re.sub(r",(\s*[.!?])", r"\1", out)
    return out.strip()


def _capitalize_first(text: str) -> str:
    if not text:
        return text
    return text[0].upper() + text[1:]


def _avg_sentence_length(text: str) -> float:
    sentences = [s for s in re.split(r"[.!?]+", text) if s.strip()]
    if not sentences:
        return 0.0
    return sum(len(s.split()) for s in sentences) / len(sentences)


def _count_specifics(text: str) -> int:
    return len(EVIDENCE_PATTERN.findall(text))


def _count_hedges(text: str) -> int:
    return len(HEDGE_PATTERN.findall(text))


def _opportunity_keywords(config: dict) -> set[str]:
    text = (config.get("opportunity_description") or "").lower()
    if not text:
        return set()
    words = re.findall(r"[a-z]{4,}", text)
    stop = {
        "this", "that", "with", "from", "have", "your", "about", "they",
        "their", "should", "would", "could", "while", "where", "which",
        "applicants", "summer", "early", "looking", "interested", "role",
        "able", "into",
    }
    return {w for w in words if w not in stop}


def _short_phrase(text: str) -> str:
    """Pull a short, quotable phrase from the user's answer for personalized drills."""
    m = PROJECT_VERB_PATTERN.search(text)
    if m:
        return m.group(2).strip().rstrip(".,!?;:'\"")
    words = text.split()
    snippet = " ".join(words[:6]).strip(".,!?;:'\"")
    return snippet or "your answer"


def _build_headline_from_answer(answer: str, config: dict) -> str:
    """Build a one-sentence headline using the user's actual content.

    Designed to never fabricate prior experience: when no project verb is
    found in the answer, the fallback frames the rewrite as "what I would
    say with more time" rather than asserting work history.
    """
    interview_type = config["interview_type"].lower()
    m = PROJECT_VERB_PATTERN.search(answer)
    if m:
        verb = m.group(1).lower()
        thing = m.group(2).strip().rstrip(".,!?;:'\"")
        return (
            f"Here is the short version: I {verb} {thing}, and that is "
            "the experience I want to build on here."
        )
    return (
        f"Here is the short version: this {interview_type} matters to me, "
        "and here is the most honest version of what I would say with "
        "another minute to think."
    )


def _build_bridge(config: dict) -> str:
    """Build a one-sentence bridge tying the answer back to the opportunity."""
    opp = (config.get("opportunity_description") or "").strip()
    interview_type = config["interview_type"].lower()
    if not opp:
        return (
            f"That matters here because this {interview_type} is exactly "
            "the kind of role where I want to keep getting better."
        )
    sentence = re.split(r"[.!?]", opp)[0].strip().rstrip(",")
    if len(sentence) > 110:
        sentence = sentence[:107].rsplit(" ", 1)[0] + "..."
    return (
        f"That matters for this role because it is about {sentence.lower()} "
        "— and that is exactly the kind of work I want to keep getting "
        "better at."
    )


def _build_improved_answer(weakest_turn: dict, config: dict) -> dict:
    """Actually transform the user's weakest answer into a rewrite."""
    original = _answer_text(weakest_turn) or "(no written explanation provided)"
    cleaned = _strip_hedges(original)
    cleaned = _capitalize_first(cleaned)
    if cleaned and cleaned[-1] not in ".!?":
        cleaned += "."
    headline = _build_headline_from_answer(original, config)
    bridge = _build_bridge(config)
    rewrite = f"{headline} {cleaned} {bridge}"
    return {
        "original_question": _question_text(weakest_turn),
        "rewrite": rewrite,
        "what_changed": (
            "Added a one-sentence headline up front so the listener knows "
            "where you are going. Stripped hedging words like 'just', "
            "'maybe', 'kind of', and 'I think' without changing your facts. "
            "Closed with a one-line bridge tying your experience to what "
            "this opportunity is actually asking for."
        ),
    }


def _personalized_drills(config: dict, transcript: list[dict]) -> list[dict]:
    """Three drills, at least one of which quotes the user's actual content."""
    if not transcript:
        return []
    longest = max(transcript, key=lambda t: len(_answer_text(t)))
    weakest = min(transcript, key=lambda t: len(_answer_text(t)))
    snippet = _short_phrase(_answer_text(longest))
    weakest_q = _question_text(weakest)
    short_q = (weakest_q[:65] + "...") if len(weakest_q) > 65 else weakest_q
    return [
        {
            "drill": (
                f"Re-record your answer about {snippet} in 90 seconds, "
                "using the structure: point, example, takeaway."
            ),
            "why_this_helps": (
                "You already have the material — this drill makes the "
                "strongest part land first instead of getting buried at "
                "the end."
            ),
        },
        {
            "drill": (
                f"Take your shortest answer (to '{short_q}') and rewrite "
                "it with one concrete detail (a name, a number, or a "
                "result). Practice it out loud."
            ),
            "why_this_helps": (
                "Short answers are usually missing one specific that "
                "would make them memorable to the interviewer."
            ),
        },
        {
            "drill": (
                "Re-read every answer and delete every hedging word "
                "('maybe', 'just', 'kind of', 'I guess', 'I think')."
            ),
            "why_this_helps": (
                "Removes verbal shrinking so your real point lands "
                "without you sounding arrogant."
            ),
        },
    ]


def _score_qualitative_rubric(config: dict, qual_turns: list[dict]) -> dict:
    """Score the 8 qualitative rubric items with real differentiators."""
    full_text = " ".join(_answer_text(t) for t in qual_turns)
    word_counts = [len(_answer_text(t).split()) for t in qual_turns]
    total_words = sum(word_counts)
    avg_words = total_words / max(len(qual_turns), 1)
    avg_sentence = sum(
        _avg_sentence_length(_answer_text(t)) for t in qual_turns
    ) / max(len(qual_turns), 1)
    specifics = _count_specifics(full_text)
    hedges = _count_hedges(full_text)
    hedge_density = hedges / max(total_words, 1) * 100
    has_motivation = bool(MOTIVATION_PATTERN.search(full_text))
    has_learning = bool(LEARNING_PATTERN.search(full_text))
    structure_hits = len(STRUCTURE_PATTERN.findall(full_text))
    has_structure = structure_hits >= 2
    opp_kw = _opportunity_keywords(config)
    has_opp_overlap = (
        any(w in full_text.lower() for w in opp_kw) if opp_kw else has_motivation
    )

    if 12 <= avg_sentence <= 22 and total_words >= 80:
        clarity_score, clarity_fb = 5, (
            "Sentences are easy to follow with a steady rhythm. Keep this length."
        )
    elif avg_sentence > 30:
        clarity_score, clarity_fb = 2, (
            "Sentences run long; listeners lose the point. Break them into 12-20 word units."
        )
    elif total_words < 30:
        clarity_score, clarity_fb = 1, (
            "Answers are too short to land a clear point. Aim for 2-4 sentences per question."
        )
    elif 8 <= avg_sentence < 12 or 22 < avg_sentence <= 30:
        clarity_score, clarity_fb = 4, (
            "Mostly clear. Open each answer with one short sentence that states the point."
        )
    else:
        clarity_score, clarity_fb = 3, (
            "Clear enough, but uneven. Pick a default sentence length and stick to it."
        )

    if specifics >= 6:
        specificity_score, specificity_fb = 5, (
            "You backed claims with concrete artifacts. This is what makes answers stick."
        )
    elif specifics >= 3:
        specificity_score, specificity_fb = 4, (
            "Decent specifics. Aim for at least one concrete artifact "
            "(a project name, a number, a result) per answer."
        )
    elif specifics >= 1:
        specificity_score, specificity_fb = 3, (
            "You have one or two specifics. Spread them across every answer, not just one."
        )
    else:
        specificity_score, specificity_fb = 1, (
            "Answers stayed abstract. Always lead with what you actually built, wrote, or did."
        )

    if hedge_density < 1.5 and total_words >= 60:
        confidence_score, confidence_fb = 5, (
            "Almost no hedging — your point lands without you stepping on it."
        )
    elif hedge_density < 3:
        confidence_score, confidence_fb = 4, (
            "Mostly confident. Trim a few more 'just', 'maybe', or 'kind of' for impact."
        )
    elif hedge_density < 5:
        confidence_score, confidence_fb = 3, (
            "Several hedges per answer. Each one shrinks your point. Cut them in your next pass."
        )
    elif hedge_density < 8:
        confidence_score, confidence_fb = 2, (
            "Frequent hedging — try saying the same idea once, in plain words, with no qualifiers."
        )
    else:
        confidence_score, confidence_fb = 1, (
            "Heavy hedging. Practice rewriting one answer with zero hedge words and reading it aloud."
        )

    if has_opp_overlap and has_motivation:
        relevance_score, relevance_fb = 5, (
            "You connected your stories to what the opportunity is actually about. Keep doing this."
        )
    elif has_opp_overlap or has_motivation:
        relevance_score, relevance_fb = 4, (
            "Tie each story back to a specific phrase from the opportunity description, not just the role in general."
        )
    elif total_words >= 60:
        relevance_score, relevance_fb = 3, (
            "You said real things, but the listener has to do the work of connecting them to this role."
        )
    else:
        relevance_score, relevance_fb = 2, (
            "Add a one-line bridge to the role at the end of each answer."
        )

    if total_words >= 100 and has_learning:
        authenticity_score, authenticity_fb = 5, (
            "Your voice comes through honestly with real reflection. Keep this — you do not need to sound like anyone else."
        )
    else:
        authenticity_score, authenticity_fb = 4, (
            "Your voice is honest. Keep it — interviewers prefer specific over polished."
        )

    if has_structure and avg_words >= 60:
        structure_score, structure_fb = 5, (
            "Strong structural markers ('first', 'then', 'so I', 'the result') — listeners can follow you without effort."
        )
    elif has_structure or avg_words >= 50:
        structure_score, structure_fb = 4, (
            "Some structure. Try the explicit frame: situation, what I did, what I learned."
        )
    elif avg_words >= 25:
        structure_score, structure_fb = 3, (
            "Use a simple frame so long answers do not drift: situation, what you did, what you learned."
        )
    else:
        structure_score, structure_fb = 2, (
            "Answers are too short to need much structure — start by getting them to 3-4 sentences first."
        )

    if specifics >= 5 and has_learning:
        evidence_score, evidence_fb = 5, (
            "Real examples plus reflection on what you learned — this is the strongest combo."
        )
    elif specifics >= 3:
        evidence_score, evidence_fb = 4, (
            "Good evidence. Pair each example with one sentence on what you took away from it."
        )
    elif specifics >= 1:
        evidence_score, evidence_fb = 3, (
            "You have an example. Use it earlier in the answer instead of saving it for last."
        )
    else:
        evidence_score, evidence_fb = 1, (
            "No concrete examples yet. 'I built X to do Y' beats 'I am interested in X' every time."
        )

    if has_learning and total_words >= 80:
        growth_score, growth_fb = 5, (
            "You named what you learned and what you would do differently — exactly what interviewers listen for."
        )
    elif has_learning:
        growth_score, growth_fb = 4, (
            "Some reflection. Make it more concrete: what was the mistake, what changed?"
        )
    elif total_words >= 60:
        growth_score, growth_fb = 3, (
            "Add one moment where you got something wrong and what changed because of it."
        )
    else:
        growth_score, growth_fb = 2, (
            "No reflection visible yet. End at least one answer with 'I learned that...' or 'next time I would...'."
        )

    return {
        "clarity": {"score": clarity_score, "feedback": clarity_fb},
        "specificity": {"score": specificity_score, "feedback": specificity_fb},
        "confidence": {"score": confidence_score, "feedback": confidence_fb},
        "relevance": {"score": relevance_score, "feedback": relevance_fb},
        "authenticity": {"score": authenticity_score, "feedback": authenticity_fb},
        "structure": {"score": structure_score, "feedback": structure_fb},
        "evidence_examples": {"score": evidence_score, "feedback": evidence_fb},
        "growth_mindset": {"score": growth_score, "feedback": growth_fb},
    }


def _score_technical_rubric(tech_turns: list[dict]) -> dict:
    """Score the 2 technical rubric items based on correctness + reasoning."""
    if not tech_turns:
        return {}
    correct_count = 0
    answered_count = 0
    reasoning_lengths: list[int] = []
    for turn in tech_turns:
        q = _question_obj(turn)
        sel = _selected_choice(turn)
        if sel is not None:
            answered_count += 1
            correct_label = q.get("_correct_label")
            if correct_label and sel == correct_label:
                correct_count += 1
        reasoning_lengths.append(len(_answer_text(turn).split()))
    accuracy = correct_count / max(answered_count, 1)
    avg_reasoning = sum(reasoning_lengths) / max(len(reasoning_lengths), 1)

    # Technical correctness
    if accuracy >= 0.9:
        tc_score, tc_fb = 5, (
            "Strong correctness across the technical questions. Keep checking units and edge cases."
        )
    elif accuracy >= 0.6:
        tc_score, tc_fb = 4, (
            "Solid majority correct. Re-derive the misses from first principles to lock them in."
        )
    elif accuracy >= 0.4:
        tc_score, tc_fb = 3, (
            "Mixed results. Use the question reviews below to study the misses one at a time."
        )
    elif answered_count == 0:
        tc_score, tc_fb = 2, (
            "No technical answers selected — pick something even if you are unsure, then explain why."
        )
    else:
        tc_score, tc_fb = 2, (
            "Most technical questions were missed. Slow down on the next pass and write the formula or steps before choosing."
        )

    # Technical reasoning
    if avg_reasoning >= 35:
        tr_score, tr_fb = 5, (
            "You wrote real reasoning, not just a one-line guess. That is what makes your answer evaluable."
        )
    elif avg_reasoning >= 18:
        tr_score, tr_fb = 4, (
            "Decent reasoning. State your assumption, the formula or step, and the conclusion in two short sentences."
        )
    elif avg_reasoning >= 8:
        tr_score, tr_fb = 3, (
            "Reasoning is too brief to evaluate. Even one extra sentence ('I picked A because the variance scales as ...') changes the impression entirely."
        )
    else:
        tr_score, tr_fb = 2, (
            "Almost no written reasoning. Always show at least one line of why — even when you are sure."
        )
    return {
        "technical_reasoning": {"score": tr_score, "feedback": tr_fb},
        "technical_correctness": {"score": tc_score, "feedback": tc_fb},
    }


def _build_question_reviews(config: dict, transcript: list[dict]) -> list[dict]:
    """One review per question. Technical reviews include correct answer."""
    reviews = []
    for i, turn in enumerate(transcript):
        q = _question_obj(turn)
        qtype = q.get("question_type", "qualitative")
        ans_text = _answer_text(turn)
        words = len(ans_text.split())
        if qtype == "technical":
            sel = _selected_choice(turn)
            correct_label = q.get("_correct_label")
            correct_text = None
            if correct_label and q.get("choices"):
                for c in q["choices"]:
                    if c.get("label") == correct_label:
                        correct_text = f"{correct_label}. {c.get('text', '')}"
                        break
            if correct_label is None:
                # Mock didn't carry an answer key (rare — Live mode question
                # without scorer-provided correctness). Be honest about that.
                what_well = (
                    "You picked an option and explained your thinking — "
                    "that is the right behavior even when you are unsure."
                ) if sel else (
                    "Even reading the choices counts as engagement; "
                    "next time, pick one and defend it briefly."
                )
                what_to = (
                    "I cannot verify correctness without a stored answer "
                    "key for this item. Re-derive the answer with a clean "
                    "sheet of paper to confirm."
                )
                reviews.append({
                    "question_index": i,
                    "question_type": "technical",
                    "what_went_well": what_well,
                    "what_to_improve": what_to,
                    "correct_answer_if_applicable": None,
                    "explanation_if_applicable": None,
                })
                continue
            correct = (sel is not None) and (sel == correct_label)
            if correct:
                what_well = (
                    f"You picked {sel} and that is the right answer. "
                    f"Your reasoning ({words} words) is the kind of "
                    "explanation that locks in the concept."
                )
                what_to = (
                    "Tighten your reasoning to one or two sentences so it "
                    "lands fast in a real interview."
                )
            else:
                what_well = (
                    "You committed to a choice and wrote an explanation — "
                    "that is what a real interviewer wants to evaluate."
                )
                what_to = (
                    f"You picked {sel or '(none)'}, but the correct answer "
                    f"is {correct_label}. Re-derive it on paper using the "
                    "explanation below; that is how you stop missing this "
                    "type next time."
                )
            reviews.append({
                "question_index": i,
                "question_type": "technical",
                "what_went_well": what_well,
                "what_to_improve": what_to,
                "correct_answer_if_applicable": correct_text,
                "explanation_if_applicable": q.get("_correct_explanation"),
            })
        else:
            specifics = _count_specifics(ans_text)
            hedges = _count_hedges(ans_text)
            if words >= 60 and specifics >= 2:
                what_well = (
                    "Real length, real examples — this answer would land "
                    "in a real interview."
                )
            elif words >= 30:
                what_well = (
                    "You said something concrete, which is most of the "
                    "battle for an early-career interview."
                )
            else:
                what_well = (
                    "You answered honestly and that is more than most "
                    "first-time interviewees do — now we build from here."
                )
            issue_bits = []
            if words < 30:
                issue_bits.append("add 2-3 more sentences with one specific example")
            if hedges >= 3:
                issue_bits.append("trim hedges like 'just', 'maybe', 'kind of'")
            if specifics == 0:
                issue_bits.append("name a real project, class, or moment")
            what_to = (
                "; ".join(issue_bits)
                if issue_bits
                else "tie the last sentence back to what this opportunity is actually about"
            )
            reviews.append({
                "question_index": i,
                "question_type": "qualitative",
                "what_went_well": what_well,
                "what_to_improve": what_to[:1].upper() + what_to[1:] + ".",
                "correct_answer_if_applicable": None,
                "explanation_if_applicable": None,
            })
    return reviews


def _pick_strongest_moment(transcript: list[dict]) -> str:
    if not transcript:
        return "No answers yet."
    scored = [
        (i, _count_specifics(_answer_text(t)) * 2 + len(_answer_text(t).split()))
        for i, t in enumerate(transcript)
    ]
    best_idx = max(scored, key=lambda x: x[1])[0]
    q = _question_text(transcript[best_idx])
    short_q = (q[:80] + "...") if len(q) > 80 else q
    return (
        f"Your answer to '{short_q}' showed the most depth. Build other "
        "answers to match its level of detail and specificity."
    )


def _pick_biggest_issue(rubric: dict) -> str:
    if not rubric:
        return "No rubric data yet."
    weakest_key, weakest = min(rubric.items(), key=lambda x: x[1]["score"])
    label = dict(RUBRIC_CATEGORIES).get(weakest_key, weakest_key)
    return (
        f"Your weakest dimension is **{label}** ({weakest['score']}/5). "
        f"{weakest['feedback']}"
    )


def _neutral_rubric_item(label: str, kind: str) -> dict:
    if kind == "qualitative":
        return {
            "score": 3,
            "feedback": (
                "No qualitative answers in this interview, so this dimension "
                "was not directly assessed."
            ),
        }
    return {
        "score": 3,
        "feedback": (
            "No technical questions in this interview, so this dimension "
            "was not directly assessed."
        ),
    }


def mock_feedback(config: dict, plan: dict, transcript: list[dict]) -> dict:
    qual_turns = [t for t in transcript if _question_type(t) == "qualitative"]
    tech_turns = [t for t in transcript if _question_type(t) == "technical"]

    rubric: dict = {}
    if qual_turns:
        rubric.update(_score_qualitative_rubric(config, qual_turns))
    if tech_turns:
        rubric.update(_score_technical_rubric(tech_turns))

    for key, label in RUBRIC_CATEGORIES:
        if key not in rubric:
            kind = "technical" if key in TECHNICAL_RUBRIC_KEYS else "qualitative"
            rubric[key] = _neutral_rubric_item(label, kind)

    overall = int(round(sum(r["score"] for r in rubric.values()) / (len(rubric) * 5) * 100))

    weakest_pool = qual_turns or transcript
    weakest = min(weakest_pool, key=lambda t: len(_answer_text(t)))
    longest = max(transcript, key=lambda t: len(_answer_text(t)))

    summary_bits = []
    if qual_turns:
        summary_bits.append(
            "front-load specifics and tie each story to what the opportunity is asking for"
        )
    if tech_turns:
        summary_bits.append(
            "for technical items, write one or two sentences of reasoning before picking"
        )
    summary = (
        "You have real substance to work with. The biggest unlocks are: "
        + "; ".join(summary_bits)
        + ". Keep your voice. Tighten the structure."
    )

    return {
        "overall_score": overall,
        "overall_summary": summary,
        "rubric": rubric,
        "question_reviews": _build_question_reviews(config, transcript),
        "strongest_moment": _pick_strongest_moment(transcript),
        "biggest_issue": _pick_biggest_issue(rubric),
        "improved_answer": _build_improved_answer(weakest, config),
        "targeted_drills": _personalized_drills(config, transcript),
        "next_practice_question": (
            f"Building on your answer about {_short_phrase(_answer_text(longest))}: "
            "tell me about a time you kept going on something hard when you "
            "did not have anyone around to help you figure it out."
        ),
        "ethical_reminder": (
            "This is coaching, not a hiring decision. You do not need to "
            "change your voice, identity, or background to be taken "
            "seriously. For technical questions, double-check correctness "
            "yourself — this tool can make math mistakes."
        ),
    }


def score_interview(config: dict, plan: dict, transcript: list[dict]) -> dict:
    """Score the interview and return a structured rubric + question reviews."""
    if not has_api_key():
        return mock_feedback(config, plan, transcript)

    rubric_keys = ", ".join(k for k, _ in RUBRIC_CATEGORIES)
    system = (
        ETHICAL_GUARDRAILS
        + "\nYou are scoring a mock interview. Return ONLY valid JSON with "
        "this exact shape:\n"
        "{\n"
        '  "overall_score": 0-100 integer,\n'
        '  "overall_summary": string,\n'
        f'  "rubric": {{ {rubric_keys}: each {{"score": 1-5, "feedback": string}} }},\n'
        '  "question_reviews": [\n'
        '     {"question_index": int, "question_type": "qualitative"|"technical",\n'
        '      "what_went_well": string, "what_to_improve": string,\n'
        '      "correct_answer_if_applicable": string|null,\n'
        '      "explanation_if_applicable": string|null}\n'
        '  ],\n'
        '  "strongest_moment": string,\n'
        '  "biggest_issue": string,\n'
        '  "improved_answer": {"original_question": string, "rewrite": string, "what_changed": string},\n'
        '  "targeted_drills": [{"drill": string, "why_this_helps": string}],\n'
        '  "next_practice_question": string,\n'
        '  "ethical_reminder": string\n'
        "}\n"
        "Rules:\n"
        "- The improved_answer rewrite MUST preserve the user's actual facts. Do NOT invent achievements.\n"
        "- For technical questions, identify the correct option in correct_answer_if_applicable "
        "(e.g. 'B. ...') and explain why in explanation_if_applicable.\n"
        "- For qualitative questions, set correct_answer_if_applicable and explanation_if_applicable to null.\n"
        "- If you are uncertain about correctness, say so clearly in explanation_if_applicable.\n"
        "- For technical_reasoning and technical_correctness rubric items, "
        "score based ONLY on the technical questions. If there are no technical "
        "questions, set both to score 3 and explain that.\n"
    )
    user = (
        f"{_config_block(config)}\n"
        f"{_plan_block(plan)}\n\n"
        f"Full transcript:\n{_transcript_block(transcript)}\n\n"
        "Score the interview now."
    )
    try:
        data = call_claude_json(system, user)
        validated = Feedback(**data)
        return validated.model_dump()
    except (ValidationError, Exception):  # noqa: BLE001
        return mock_feedback(config, plan, transcript)


# ---------------------------------------------------------------------------
# Streamlit session helpers
# ---------------------------------------------------------------------------


def _init_state() -> None:
    defaults = {
        "interview_started": False,
        "interview_complete": False,
        "question_index": 0,
        "current_question": None,           # dict (Question) or None
        "current_question_note": "",
        "transcript": [],
        "feedback": None,
        "config": None,
        "interview_plan": None,
        "pending_sample": None,
        "question_start_time": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_interview() -> None:
    """Clear all interview state. Setup fields are preserved."""
    st.session_state.interview_started = False
    st.session_state.interview_complete = False
    st.session_state.question_index = 0
    st.session_state.current_question = None
    st.session_state.current_question_note = ""
    st.session_state.transcript = []
    st.session_state.feedback = None
    st.session_state.config = None
    st.session_state.interview_plan = None
    st.session_state.question_start_time = None


def _bump_difficulty(current: str) -> str:
    try:
        idx = DIFFICULTY_LADDER.index(current)
    except ValueError:
        return current
    return DIFFICULTY_LADDER[min(idx + 1, len(DIFFICULTY_LADDER) - 1)]


def _build_markdown_export(
    config: dict, plan: dict, transcript: list[dict], feedback: dict
) -> str:
    """Compose the feedback dashboard as a single Markdown document."""
    lines = [
        "# InterviewOS — Practice Report",
        "",
        f"**Interview type:** {config['interview_type']}  ",
        f"**Mode:** {plan.get('resolved_mode', '?')}  ",
        f"**Difficulty:** {plan.get('resolved_difficulty', '?')}  ",
        f"**Questions:** {plan.get('resolved_question_count', '?')}  ",
        f"**Timer:** "
        + (
            f"{plan.get('resolved_timer_seconds')}s/question"
            if plan.get("resolved_timer_seconds")
            else "off"
        ),
        "",
        "## Overall",
        f"- **Score:** {feedback['overall_score']}/100",
        f"- **Summary:** {feedback['overall_summary']}",
        "",
        "## Rubric",
    ]
    for key, label in RUBRIC_CATEGORIES:
        item = feedback["rubric"].get(key, {})
        lines.append(
            f"- **{label}:** {item.get('score', '?')}/5 — {item.get('feedback', '')}"
        )
    lines += [
        "",
        "## Strongest moment",
        feedback["strongest_moment"],
        "",
        "## Biggest issue",
        feedback["biggest_issue"],
        "",
        "## Question-by-question review",
    ]
    for review in feedback.get("question_reviews", []):
        i = review["question_index"]
        if 0 <= i < len(transcript):
            qt = _question_text(transcript[i])
        else:
            qt = "(question text unavailable)"
        lines.append(f"### Q{i + 1} ({review['question_type']}): {qt}")
        lines.append(f"- **What went well:** {review['what_went_well']}")
        lines.append(f"- **What to improve:** {review['what_to_improve']}")
        if review.get("correct_answer_if_applicable"):
            lines.append(
                f"- **Correct answer:** {review['correct_answer_if_applicable']}"
            )
        if review.get("explanation_if_applicable"):
            lines.append(
                f"- **Explanation:** {review['explanation_if_applicable']}"
            )
        lines.append("")
    lines += [
        "## Improved answer (rewrite)",
        f"**Original question:** {feedback['improved_answer']['original_question']}",
        "",
        f"**Rewrite:** {feedback['improved_answer']['rewrite']}",
        "",
        f"**What changed:** {feedback['improved_answer']['what_changed']}",
        "",
        "## Targeted drills",
    ]
    for d in feedback["targeted_drills"]:
        lines.append(f"- **{d['drill']}**")
        lines.append(f"  - _Why this helps:_ {d['why_this_helps']}")
    lines += [
        "",
        "## Next practice question",
        feedback["next_practice_question"],
        "",
        "## Ethical reminder",
        feedback["ethical_reminder"],
        "",
        "## Full transcript",
    ]
    for i, t in enumerate(transcript, 1):
        q = _question_obj(t)
        lines.append(f"**Q{i} ({q.get('question_type', 'qualitative')}).** {q.get('question_text', '')}")
        if q.get("answer_format") == "multiple_choice_with_explanation":
            for c in q.get("choices", []):
                lines.append(f"  - {c['label']}. {c['text']}")
            sel = _selected_choice(t)
            lines.append(f"  - **Selected:** {sel or '(none)'}")
        lines.append("")
        lines.append(f"> {_answer_text(t)}")
        lines.append("")
    return "\n".join(lines)


def _load_sample_feedback_into_state() -> None:
    """Populate session state with a canned interview + feedback for judges."""
    st.session_state.config = SAMPLE_REPORT_CONFIG
    st.session_state.interview_plan = SAMPLE_REPORT_PLAN
    st.session_state.transcript = list(SAMPLE_REPORT_TRANSCRIPT)
    st.session_state.feedback = mock_feedback(
        SAMPLE_REPORT_CONFIG, SAMPLE_REPORT_PLAN, list(SAMPLE_REPORT_TRANSCRIPT)
    )
    st.session_state.interview_started = True
    st.session_state.interview_complete = True
    st.session_state.current_question = None
    st.session_state.current_question_note = ""
    st.session_state.question_index = SAMPLE_REPORT_PLAN["resolved_question_count"]
    st.session_state.pending_sample = None
    st.session_state.question_start_time = None


# ---------------------------------------------------------------------------
# UI: CSS
# ---------------------------------------------------------------------------


CUSTOM_CSS = """
<style>
.block-container {
    max-width: 940px;
    margin: 0 auto;
    padding-top: 2rem;
    padding-left: 1.5rem;
    padding-right: 1.5rem;
}

/* Hero with gradient background */
.io-hero {
    padding: 1.5rem 1.6rem;
    border-radius: 18px;
    background: linear-gradient(135deg, #EEF2FF 0%, #FAF5FF 60%, #FDF4FF 100%);
    border: 1px solid #E0E7FF;
    margin-bottom: 1rem;
    box-shadow: 0 4px 18px rgba(99, 102, 241, 0.06);
}
.io-hero h1 {
    font-size: 2.5rem; font-weight: 800; letter-spacing: -0.02em;
    margin: 0.1rem 0 0.25rem 0; line-height: 1.15;
    background: linear-gradient(120deg, #1E1B4B, #6366F1 80%);
    -webkit-background-clip: text; background-clip: text;
    -webkit-text-fill-color: transparent;
}
.io-hero .io-sub { font-size: 1.05rem; color: #334155; margin-bottom: 0.25rem; }
.io-hero .io-impact { font-size: 0.92rem; color: #475569; font-style: italic; }

/* Badges */
.io-badge-wrap { margin-bottom: 0.6rem; line-height: 1.6; }
.io-badge {
    display: inline-block; padding: 5px 12px; border-radius: 999px;
    font-size: 0.78rem; font-weight: 600; letter-spacing: 0.02em;
    line-height: 1.4;
}
.io-badge-demo { background: #FEF3C7; color: #92400E; border: 1px solid #FDE68A; }
.io-badge-live { background: #DCFCE7; color: #166534; border: 1px solid #BBF7D0; }
.io-badge-interview {
    display: inline-block; padding: 4px 10px; border-radius: 999px;
    background: #DBEAFE; color: #1E40AF; border: 1px solid #BFDBFE;
    font-size: 0.72rem; font-weight: 700; letter-spacing: 0.03em;
    margin-left: 0.5rem; vertical-align: middle;
}

/* Generic cards */
.io-card {
    background: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 14px;
    padding: 1.1rem 1.2rem; margin-bottom: 0.9rem;
    box-shadow: 0 2px 8px rgba(15, 23, 42, 0.03);
}
.io-card h4 { margin: 0 0 0.4rem 0; font-size: 1.0rem; font-weight: 700; color: #0F172A; }
.io-card p, .io-card li { color: #374151; font-size: 0.95rem; line-height: 1.5; }
.io-muted { color: #6B7280; font-size: 0.85rem; }
.io-section-title { font-weight: 700; font-size: 1.15rem; margin: 1.4rem 0 0.5rem 0; color: #111827; }

/* Plan card */
.io-plan {
    background: linear-gradient(135deg, #F0F9FF 0%, #ECFDF5 100%);
    border: 1px solid #BAE6FD;
    border-radius: 14px; padding: 1rem 1.2rem; margin-bottom: 0.8rem;
}
.io-plan h4 { margin: 0 0 0.5rem 0; color: #075985; font-size: 1.0rem; font-weight: 700; }
.io-plan .io-plan-grid {
    display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 0.5rem 1rem; margin: 0.5rem 0 0.6rem 0;
}
.io-plan .io-plan-cell { font-size: 0.85rem; color: #1E40AF; }
.io-plan .io-plan-cell strong { color: #0C4A6E; }
.io-plan p { font-size: 0.88rem; color: #0F172A; margin: 0.4rem 0 0 0; }

/* Animated avatar + speech bubble */
.io-avatar-row {
    display: flex; align-items: flex-start; gap: 18px;
    margin: 0.8rem 0 1rem 0;
}
.io-avatar {
    width: 78px; height: 78px; border-radius: 50%;
    background: linear-gradient(135deg, #6366F1 0%, #8B5CF6 100%);
    position: relative;
    box-shadow: 0 8px 20px rgba(99, 102, 241, 0.28);
    animation: io-float 3.4s ease-in-out infinite;
    flex-shrink: 0;
}
/* Eyes */
.io-avatar::before, .io-avatar::after {
    content: '';
    position: absolute;
    width: 9px; height: 9px;
    background: #FFFFFF;
    border-radius: 50%;
    top: 28px;
    animation: io-blink 4.6s infinite;
    transform-origin: center;
}
.io-avatar::before { left: 21px; }
.io-avatar::after { right: 21px; }
.io-avatar .io-mouth {
    position: absolute;
    width: 24px; height: 10px;
    border-bottom: 2.5px solid #FFFFFF;
    border-radius: 0 0 24px 24px;
    bottom: 18px; left: 27px;
}
@keyframes io-float {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-7px); }
}
@keyframes io-blink {
    0%, 92%, 100% { transform: scaleY(1); }
    94%, 96% { transform: scaleY(0.1); }
}

.io-speech {
    position: relative;
    background: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-left: 4px solid #6366F1;
    border-radius: 14px;
    padding: 14px 18px;
    box-shadow: 0 4px 14px rgba(15, 23, 42, 0.06);
    flex: 1;
    animation: io-pulse 4s ease-in-out infinite;
}
.io-speech::before {
    content: '';
    position: absolute;
    top: 22px; left: -10px;
    width: 0; height: 0;
    border-top: 10px solid transparent;
    border-bottom: 10px solid transparent;
    border-right: 10px solid #6366F1;
}
.io-speech::after {
    content: '';
    position: absolute;
    top: 23px; left: -8px;
    width: 0; height: 0;
    border-top: 9px solid transparent;
    border-bottom: 9px solid transparent;
    border-right: 9px solid #FFFFFF;
}
.io-speech .io-speech-text {
    color: #0F172A; font-size: 1.05rem; line-height: 1.45;
}
.io-coach-note {
    color: #64748B; font-size: 0.82rem; font-style: italic;
    margin-top: 0.55rem;
}
.io-coach-note strong { color: #475569; font-style: normal; }
@keyframes io-pulse {
    0%, 100% { box-shadow: 0 4px 14px rgba(15, 23, 42, 0.06); }
    50% { box-shadow: 0 6px 22px rgba(99, 102, 241, 0.16); }
}

/* Timer */
.io-timer {
    background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 10px;
    padding: 8px 14px; margin: 0.4rem 0 1rem 0;
    display: flex; align-items: center; gap: 14px;
    font-size: 0.85rem; color: #475569;
}
.io-timer.warning { background: #FFFBEB; border-color: #FCD34D; color: #92400E; }
.io-timer.expired { background: #FEF2F2; border-color: #FCA5A5; color: #B91C1C; font-weight: 600; }
.io-timer-label { white-space: nowrap; }
.io-timer-bar {
    flex: 1; height: 6px; background: #E2E8F0;
    border-radius: 999px; overflow: hidden;
}
.io-timer-fill {
    height: 100%;
    background: linear-gradient(90deg, #10B981 0%, #F59E0B 70%, #EF4444 100%);
    transform-origin: left center;
}
@keyframes io-timer-shrink {
    from { width: 100%; }
    to { width: 0%; }
}

/* Locked answer view (shown between submit and next-question load) */
.io-locked-meta {
    color: #475569; font-size: 0.85rem;
    background: #F1F5F9; border: 1px solid #E2E8F0;
    border-radius: 8px; padding: 6px 12px;
    margin-bottom: 0.4rem; display: inline-block;
}

/* Rubric grid */
.io-rubric {
    border: 1px solid #E5E7EB; border-radius: 12px; padding: 0.8rem 0.95rem;
    background: #FFFFFF; height: 100%;
    box-shadow: 0 1px 4px rgba(15, 23, 42, 0.03);
}
.io-rubric .io-rubric-title { font-weight: 700; font-size: 0.95rem; margin-bottom: 0.15rem; color: #111827; }
.io-rubric .io-rubric-score { font-size: 1.4rem; font-weight: 800; color: #2563EB; }
.io-rubric .io-rubric-feedback { color: #374151; font-size: 0.85rem; margin-top: 0.4rem; }

.io-bar { background: #E5E7EB; border-radius: 999px; height: 6px; margin-top: 0.4rem; overflow: hidden; }
.io-bar-fill {
    background: linear-gradient(90deg, #6366F1, #8B5CF6);
    height: 100%;
}

/* Question review cards */
.io-qreview {
    background: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 12px;
    padding: 0.95rem 1.1rem; margin-bottom: 0.7rem;
}
.io-qreview .io-qreview-meta { font-size: 0.78rem; color: #64748B; letter-spacing: 0.04em; text-transform: uppercase; font-weight: 700; margin-bottom: 0.3rem; }
.io-qreview h4 { margin: 0 0 0.5rem 0; font-size: 0.98rem; color: #0F172A; }
.io-qreview .io-qreview-row { font-size: 0.9rem; margin: 0.25rem 0; }
.io-qreview .io-qreview-correct { color: #166534; font-weight: 600; }
.io-qreview .io-qreview-wrong { color: #B91C1C; font-weight: 600; }

footer { visibility: hidden; }
</style>
"""


# ---------------------------------------------------------------------------
# UI: helpers
# ---------------------------------------------------------------------------


def render_demo_badge() -> str:
    """Return the HTML for the Demo Mode / Live mode pill."""
    if has_api_key():
        return '<span class="io-badge io-badge-live">Live mode &mdash; Anthropic API connected</span>'
    return '<span class="io-badge io-badge-demo">Demo Mode &mdash; no API key, deterministic responses</span>'


def render_hero() -> None:
    st.markdown(
        f"""
        <div class="io-hero">
            <div class="io-badge-wrap">{render_demo_badge()}</div>
            <h1>InterviewOS</h1>
            <div class="io-sub">Practice high-stakes interviews when you do not have insider access.</div>
            <div class="io-impact">Built for students who have talent, but not always access to realistic interview practice.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_intro_cards() -> None:
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(
            """
            <div class="io-card">
                <h4>Why this matters</h4>
                <p>Many students do not lose opportunities because they lack ability.
                They lose them because their first real interview is also their first
                serious practice. InterviewOS gives students a realistic, low-stakes
                place to practice, get feedback, and try again.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col_b:
        st.markdown(
            """
            <div class="io-card">
                <h4>Why this is not just ChatGPT</h4>
                <ul>
                    <li>Structured interview environment with pacing</li>
                    <li>Adaptive follow-up questions</li>
                    <li>Technical multiple choice with written reasoning</li>
                    <li>Rendered math (LaTeX) for technical questions</li>
                    <li>Rubric-based scoring + question-by-question review</li>
                    <li>Targeted drills + ethical safeguards</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_plan_card(plan: dict) -> None:
    timer = plan.get("resolved_timer_seconds")
    timer_str = f"{timer}s/question" if timer else "Off"
    st.markdown(
        f"""
        <div class="io-plan">
            <h4>AI Interview Plan</h4>
            <div class="io-plan-grid">
                <div class="io-plan-cell"><strong>Mode:</strong> {plan.get('resolved_mode', '?')}</div>
                <div class="io-plan-cell"><strong>Difficulty:</strong> {plan.get('resolved_difficulty', '?')}</div>
                <div class="io-plan-cell"><strong>Questions:</strong> {plan.get('resolved_question_count', '?')}</div>
                <div class="io-plan-cell"><strong>Timer:</strong> {timer_str}</div>
            </div>
            <p>{plan.get('rationale', '')}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_latex_safely(latex: str | None) -> None:
    if not latex:
        return
    try:
        st.latex(latex)
    except Exception:  # noqa: BLE001 - never break the demo on bad LaTeX
        st.code(latex, language="latex")


def render_avatar_question(question_obj: dict, coach_note: str = "") -> None:
    """Render the animated avatar + speech bubble + (optional) LaTeX block."""
    text = (question_obj.get("question_text") or "").replace("\n", "<br/>")
    note = (coach_note or question_obj.get("interviewer_note", "") or "").strip()
    note_html = (
        f'<div class="io-coach-note"><strong>Coach:</strong> {note}</div>'
        if note
        else ""
    )
    st.markdown(
        f"""
        <div class="io-avatar-row">
            <div class="io-avatar"><div class="io-mouth"></div></div>
            <div class="io-speech">
                <div class="io-speech-text">{text}</div>
                {note_html}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    _render_latex_safely(question_obj.get("latex"))


@st.fragment(run_every=1.0)
def render_timer_card(total_seconds: int) -> None:
    """Live-ticking per-question timer.

    Decorated as `@st.fragment(run_every=1.0)` so the seconds text actually
    counts down once per second without re-running the whole script. Reads
    `question_start_time` from session state on each tick. The bar uses
    CSS `animation-delay: -elapsed s` so it visually shrinks smoothly
    between fragment reruns.
    """
    start_time = st.session_state.get("question_start_time")
    if not start_time or not total_seconds:
        return
    elapsed = time.time() - start_time
    remaining = max(0, int(total_seconds - elapsed))
    expired = remaining <= 0
    css_state = "expired" if expired else ("warning" if remaining <= 10 else "")
    icon = "⏰" if expired else "⏱"
    if expired:
        fill_style = "width: 0%; background: #EF4444;"
        label = "Time is up &mdash; submit your best answer or move on."
    else:
        fill_style = (
            f"animation: io-timer-shrink {total_seconds}s linear forwards; "
            f"animation-delay: -{elapsed:.2f}s; width: 100%;"
        )
        label = f"Time remaining: <strong>{remaining}s</strong> of {total_seconds}s"

    st.markdown(
        f"""
        <div class="io-timer {css_state}">
            <span class="io-timer-label">{icon} {label}</span>
            <div class="io-timer-bar"><div class="io-timer-fill" style="{fill_style}"></div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _compute_time_expired(total_seconds: int | None) -> bool:
    """Has the per-question timer expired right now? Used in the submit handler."""
    start_time = st.session_state.get("question_start_time")
    if not start_time or not total_seconds:
        return False
    return (time.time() - start_time) >= total_seconds


# ---------------------------------------------------------------------------
# Sample scenarios + canned report
# ---------------------------------------------------------------------------


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


# Canned report — Mixed interview (1 qualitative, 1 technical, 1 qualitative)
SAMPLE_REPORT_CONFIG = {
    "interview_type": "Research Program",
    "interview_mode": "Mixed",
    "difficulty": "Intermediate",
    "question_count": 3,
    "timer_seconds": 90,
    "opportunity_description": SAMPLES["research_assistant"]["opportunity_description"],
    "applicant_background": SAMPLES["research_assistant"]["applicant_background"],
}
SAMPLE_REPORT_PLAN = {
    "resolved_mode": "Mixed",
    "resolved_difficulty": "Intermediate",
    "resolved_question_count": 3,
    "resolved_timer_seconds": 90,
    "rationale": (
        "Auto-planned a mixed interview at intermediate difficulty, 3 "
        "questions, 90s timer per question, based on the description "
        "(scientific computing + early undergraduate)."
    ),
    "question_style_notes": (
        "Lead with a qualitative question about background, follow with "
        "one technical reasoning item, close with a motivation question."
    ),
    "question_types": ["qualitative", "technical", "qualitative"],
}
SAMPLE_REPORT_TRANSCRIPT = [
    {
        "question": _make_qualitative_starter({"interview_type": "Research Program"}),
        "answer": {
            "selected_choice": None,
            "written_response": (
                "I am a first-year undergraduate interested in physics and "
                "computational tools. Last semester I built a Monte Carlo "
                "option pricing simulator in Python because I wanted to see "
                "how randomness can model real systems. I learned a lot about "
                "NumPy, vectorization, and how to debug a simulation that "
                "returns plausible-but-wrong numbers."
            ),
        },
    },
    {
        "question": _public_question(TECHNICAL_QUESTION_BANK["Scientific Computing"][0]),
        "answer": {
            "selected_choice": "A",
            "written_response": (
                "Standard error of the mean of N i.i.d. samples scales like "
                "sigma over sqrt of N. To halve the error you need 4x the "
                "paths. I picked A because that matches what I saw when I "
                "doubled paths in my simulator and the noise band shrank by "
                "about a factor of 1.4."
            ),
        },
    },
    {
        "question": {
            "question_text": "Why does this research role matter to you personally?",
            "question_type": "qualitative",
            "answer_format": "free_response",
            "choices": [],
            "latex": None,
            "interviewer_note": "Probing motivation and stakes.",
        },
        "answer": {
            "selected_choice": None,
            "written_response": (
                "I come from a school where research was not really an option "
                "for undergraduates. Spending a summer alongside people who do "
                "this professionally would let me figure out if I actually "
                "want to pursue it — instead of guessing from the outside, "
                "the way I have had to guess about most things so far."
            ),
        },
    },
]


# ---------------------------------------------------------------------------
# UI: setup
# ---------------------------------------------------------------------------


def _resolve_index(options: list, value, default_index: int = 0) -> int:
    try:
        return options.index(value)
    except (ValueError, TypeError):
        return default_index


def render_setup() -> None:
    st.markdown('<div class="io-section-title">Set up your interview</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="io-muted">Pick the kind of interview you want to practice. '
        "You can also load a sample scenario, or skip ahead and see what a "
        "finished feedback report looks like.</div>",
        unsafe_allow_html=True,
    )

    st.write("")
    if st.button(
        "See a sample feedback report (no typing required)",
        use_container_width=True,
        help="Opens a pre-filled feedback dashboard so you can see the payoff in 30 seconds.",
    ):
        _load_sample_feedback_into_state()
        st.rerun()

    st.write("")
    st.markdown("**Sample scenarios**")
    s1, s2, s3 = st.columns(3)
    with s1:
        if st.button("First Internship", use_container_width=True):
            st.session_state.pending_sample = "first_internship"
            st.rerun()
    with s2:
        if st.button("Research Assistant ⭐", use_container_width=True):
            st.session_state.pending_sample = "research_assistant"
            st.rerun()
    with s3:
        if st.button("Scholarship", use_container_width=True):
            st.session_state.pending_sample = "scholarship"
            st.rerun()

    sample = SAMPLES.get(st.session_state.pending_sample) if st.session_state.pending_sample else None

    default_type = sample["interview_type"] if sample else INTERVIEW_TYPES[0]
    default_mode = sample.get("interview_mode", "Auto") if sample else "Auto"
    default_diff = sample.get("difficulty", "Auto") if sample else "Auto"
    default_count_int = sample.get("question_count") if sample else None
    default_timer_int = sample.get("timer_seconds") if sample else None
    default_opp = sample["opportunity_description"] if sample else ""
    default_bg = sample["applicant_background"] if sample else ""

    # Resolve count/timer back to the option *label* that maps to it.
    def _label_for(options: dict, value):
        for label, v in options.items():
            if v == value:
                return label
        return list(options.keys())[0]

    default_count_label = _label_for(QUESTION_COUNT_OPTIONS, default_count_int)
    default_timer_label = _label_for(TIMER_OPTIONS, default_timer_int)

    st.write("")
    col1, col2 = st.columns(2)
    with col1:
        interview_type = st.selectbox(
            "Interview type",
            INTERVIEW_TYPES,
            index=_resolve_index(INTERVIEW_TYPES, default_type, 0),
            help=(
                "Pick the closest match. 'Custom' is fine for anything not listed."
            ),
        )
    with col2:
        interview_mode = st.selectbox(
            "Interview mode",
            INTERVIEW_MODES,
            index=_resolve_index(INTERVIEW_MODES, default_mode, 0),
            help=(
                "Auto lets the AI pick based on your description. "
                "Mixed alternates qualitative and technical questions."
            ),
        )

    col3, col4 = st.columns(2)
    with col3:
        difficulty = st.selectbox(
            "Difficulty",
            DIFFICULTY_LEVELS,
            index=_resolve_index(DIFFICULTY_LEVELS, default_diff, 0),
        )
    with col4:
        question_count_label = st.selectbox(
            "Number of questions",
            list(QUESTION_COUNT_OPTIONS.keys()),
            index=_resolve_index(
                list(QUESTION_COUNT_OPTIONS.keys()), default_count_label, 0
            ),
        )

    timer_label = st.selectbox(
        "Timer",
        list(TIMER_OPTIONS.keys()),
        index=_resolve_index(list(TIMER_OPTIONS.keys()), default_timer_label, 0),
        help=(
            "Per-question timer. The bar shrinks smoothly; you can still "
            "submit after time expires."
        ),
    )

    opportunity_description = st.text_area(
        "Opportunity description (optional)",
        value=default_opp,
        height=110,
        placeholder="Paste the role description, scholarship blurb, or program summary.",
    )
    applicant_background = st.text_area(
        "Applicant background (optional)",
        value=default_bg,
        height=110,
        placeholder="A few sentences about you: experiences, projects, what you are still figuring out.",
    )

    st.write("")
    if st.button("Start interview", type="primary", use_container_width=True):
        config = {
            "interview_type": interview_type,
            "interview_mode": interview_mode,
            "difficulty": difficulty,
            "question_count": QUESTION_COUNT_OPTIONS[question_count_label],
            "timer_seconds": TIMER_OPTIONS[timer_label],
            "opportunity_description": opportunity_description,
            "applicant_background": applicant_background,
        }
        st.session_state.config = config
        st.session_state.transcript = []
        st.session_state.question_index = 0
        st.session_state.feedback = None
        st.session_state.interview_complete = False
        st.session_state.current_question_note = ""

        with st.spinner("Designing your interview..."):
            plan = plan_interview(config)
        st.session_state.interview_plan = plan
        with st.spinner("Generating your first question..."):
            q = start_interview(config, plan)
        st.session_state.current_question = q
        st.session_state.current_question_note = q.get("interviewer_note", "")
        st.session_state.question_start_time = time.time()
        st.session_state.interview_started = True
        st.session_state.pending_sample = None
        st.rerun()


# ---------------------------------------------------------------------------
# UI: interview
# ---------------------------------------------------------------------------


def _format_choice_label(choice: dict) -> str:
    return f"{choice['label']}. {choice['text']}"


def render_interview() -> None:
    config = st.session_state.config
    plan = st.session_state.interview_plan or {}
    transcript = st.session_state.transcript
    n_total = int(plan.get("resolved_question_count", DEFAULT_QUESTION_COUNT))
    answered = len(transcript)
    can_score = answered >= n_total
    current_qnum = min(answered + 1, n_total)
    current_q = st.session_state.current_question or {}

    st.markdown(
        '<div class="io-section-title">Mock interview '
        '<span class="io-badge-interview">Live Interview</span></div>',
        unsafe_allow_html=True,
    )
    progress_label = (
        f"All {n_total} answered &mdash; ready to score"
        if can_score
        else f"Question {current_qnum} of {n_total}"
    )
    st.markdown(
        f'<div class="io-muted">{config["interview_type"]} &middot; '
        f'{plan.get("resolved_mode", "?")} mode &middot; '
        f'{plan.get("resolved_difficulty", "?")} difficulty &middot; '
        f"{progress_label}</div>",
        unsafe_allow_html=True,
    )
    st.progress(answered / max(n_total, 1))

    if not can_score:
        # Avatar + speech bubble + LaTeX (if any).
        render_avatar_question(current_q, st.session_state.current_question_note)

        # Live-ticking per-question timer (st.fragment re-runs every 1s).
        timer_seconds = plan.get("resolved_timer_seconds")
        if timer_seconds and st.session_state.question_start_time:
            render_timer_card(int(timer_seconds))

        # Answer form: either MCQ + explanation, or free response.
        is_mcq = (
            current_q.get("answer_format") == "multiple_choice_with_explanation"
            and current_q.get("choices")
        )

        # The form lives inside an empty-slot placeholder so we can replace
        # it with a disabled view as soon as the user submits, while we wait
        # for the next question to load.
        form_slot = st.empty()
        with form_slot.container():
            with st.form(key=f"answer_form_{answered}", clear_on_submit=True):
                selected_choice: str | None = None
                if is_mcq:
                    choices = current_q["choices"]
                    option_labels = [_format_choice_label(c) for c in choices]
                    # `index=None` ensures no default selection — user must pick.
                    picked = st.radio(
                        "Choose one",
                        options=option_labels,
                        index=None,
                        key=f"mcq_{answered}",
                    )
                    if picked:
                        selected_choice = picked.split(".", 1)[0].strip()
                    explanation = st.text_area(
                        "Explain your reasoning briefly (required)",
                        height=140,
                        placeholder=(
                            "Even one sentence helps. State your assumption, then "
                            "why your choice follows from it."
                        ),
                    )
                else:
                    selected_choice = None
                    explanation = st.text_area(
                        "Your answer",
                        height=180,
                        placeholder="Take a breath. Answer like you would in a real interview.",
                    )

                submitted = st.form_submit_button(
                    "Submit answer", type="primary", use_container_width=True
                )

        if submitted:
            cleaned = (explanation or "").strip()
            errors = []
            if not cleaned:
                errors.append(
                    "Please write your reasoning before submitting."
                    if is_mcq
                    else "Please type an answer before submitting."
                )
            if is_mcq and not selected_choice:
                errors.append("Please select one of the choices (A, B, C, or D).")

            if errors:
                for msg in errors:
                    st.warning(msg)
            else:
                # Lock the answer area: replace the form with a disabled
                # echo of what the user submitted plus a disabled
                # "Generating next question..." button. This stays on
                # screen while next_question() runs.
                form_slot.empty()
                with form_slot.container():
                    if is_mcq:
                        st.markdown(
                            f'<div class="io-locked-meta">'
                            f"<strong>Selected:</strong> {selected_choice}"
                            f"</div>",
                            unsafe_allow_html=True,
                        )
                        st.text_area(
                            "Your reasoning (locked)",
                            value=cleaned,
                            height=140,
                            disabled=True,
                            key=f"locked_explanation_{answered}",
                        )
                    else:
                        st.text_area(
                            "Your answer (locked)",
                            value=cleaned,
                            height=180,
                            disabled=True,
                            key=f"locked_answer_{answered}",
                        )
                    st.button(
                        "⏳ Generating next question...",
                        disabled=True,
                        type="primary",
                        use_container_width=True,
                        key=f"locked_submit_{answered}",
                    )

                turn = {
                    "question": current_q,
                    "answer": {
                        "selected_choice": selected_choice,
                        "written_response": cleaned,
                        "time_expired": _compute_time_expired(timer_seconds),
                    },
                }
                st.session_state.transcript.append(turn)

                if len(st.session_state.transcript) < n_total:
                    with st.spinner("Interviewer is thinking..."):
                        nxt = next_question(config, plan, st.session_state.transcript)
                    st.session_state.current_question = nxt
                    st.session_state.current_question_note = nxt.get("interviewer_note", "")
                    st.session_state.question_start_time = time.time()
                else:
                    st.session_state.current_question = None
                    st.session_state.current_question_note = ""
                    st.session_state.question_start_time = None
                st.session_state.question_index = len(st.session_state.transcript)
                st.rerun()
    else:
        st.success(
            f"You have completed all {n_total} questions. Click below to get rubric-based feedback."
        )
        if st.button("End interview and score me", type="primary", use_container_width=True):
            with st.spinner("Scoring your interview..."):
                st.session_state.feedback = score_interview(config, plan, transcript)
            st.session_state.interview_complete = True
            st.rerun()

    if transcript:
        plural = "" if len(transcript) == 1 else "s"
        with st.expander(
            f"Transcript so far ({len(transcript)} answer{plural})",
            expanded=False,
        ):
            for i, turn in enumerate(transcript, start=1):
                q = _question_obj(turn)
                qtype = q.get("question_type", "qualitative")
                st.markdown(f"**Q{i}** *(_{qtype}_)*: {q.get('question_text', '')}")
                if q.get("answer_format") == "multiple_choice_with_explanation":
                    for c in q.get("choices", []):
                        st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;{c['label']}. {c['text']}")
                    sel = _selected_choice(turn)
                    st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;**Selected:** {sel or '(none)'}")
                st.markdown(f"> {_answer_text(turn)}")
                if i < len(transcript):
                    st.divider()

    st.write("")
    if st.button("Start over", help="Clear the interview and go back to setup."):
        reset_interview()
        st.rerun()


# ---------------------------------------------------------------------------
# UI: feedback
# ---------------------------------------------------------------------------


def render_feedback() -> None:
    feedback = st.session_state.feedback
    config = st.session_state.config
    plan = st.session_state.interview_plan or {}
    transcript = st.session_state.transcript

    st.markdown('<div class="io-section-title">Feedback dashboard</div>', unsafe_allow_html=True)
    render_plan_card(plan)

    overall = int(feedback.get("overall_score", 0))
    top_a, top_b = st.columns([1, 2])
    with top_a:
        st.metric("Overall score", f"{overall}/100")
        st.markdown(
            f'<div class="io-bar"><div class="io-bar-fill" style="width:{overall}%"></div></div>',
            unsafe_allow_html=True,
        )
    with top_b:
        st.markdown(
            f'<div class="io-card"><h4>Summary</h4><p>{feedback.get("overall_summary", "")}</p></div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div class="io-section-title">Rubric</div>', unsafe_allow_html=True)
    rubric = feedback.get("rubric", {})
    cols_per_row = 2
    items = list(RUBRIC_CATEGORIES)
    for i in range(0, len(items), cols_per_row):
        row = st.columns(cols_per_row)
        for j, (key, label) in enumerate(items[i : i + cols_per_row]):
            entry = rubric.get(key, {"score": 0, "feedback": "—"})
            score = int(entry.get("score", 0))
            fb_text = entry.get("feedback", "")
            pct = int((score / 5) * 100)
            with row[j]:
                st.markdown(
                    f"""
                    <div class="io-rubric">
                        <div class="io-rubric-title">{label}</div>
                        <div class="io-rubric-score">{score}/5</div>
                        <div class="io-bar"><div class="io-bar-fill" style="width:{pct}%"></div></div>
                        <div class="io-rubric-feedback">{fb_text}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    st.write("")
    col_s, col_b = st.columns(2)
    with col_s:
        st.markdown(
            f'<div class="io-card"><h4>Strongest moment</h4><p>{feedback.get("strongest_moment", "")}</p></div>',
            unsafe_allow_html=True,
        )
    with col_b:
        st.markdown(
            f'<div class="io-card"><h4>Biggest issue to work on</h4><p>{feedback.get("biggest_issue", "")}</p></div>',
            unsafe_allow_html=True,
        )

    # Question-by-question review
    st.markdown(
        '<div class="io-section-title">Question-by-question review</div>',
        unsafe_allow_html=True,
    )
    reviews = feedback.get("question_reviews", []) or []
    for review in reviews:
        i = int(review.get("question_index", 0))
        if 0 <= i < len(transcript):
            q = _question_obj(transcript[i])
            qt = q.get("question_text", "")
            sel = _selected_choice(transcript[i])
        else:
            q, qt, sel = {}, "(question text unavailable)", None
        qtype = review.get("question_type", q.get("question_type", "qualitative"))

        # Build the inner HTML
        rows = [
            f'<div class="io-qreview-meta">Q{i + 1} &middot; {qtype}</div>',
            f"<h4>{qt}</h4>",
        ]
        if qtype == "technical":
            correct_text = review.get("correct_answer_if_applicable") or ""
            sel_label = sel or "(none)"
            is_correct = bool(correct_text) and correct_text.startswith(f"{sel}.") if sel else False
            verdict_class = "io-qreview-correct" if is_correct else "io-qreview-wrong"
            verdict_label = "Correct" if is_correct else ("Missed" if correct_text else "Could not verify")
            rows.append(
                f'<div class="io-qreview-row"><strong>Your choice:</strong> {sel_label} '
                f'&middot; <span class="{verdict_class}">{verdict_label}</span></div>'
            )
            if correct_text:
                rows.append(
                    f'<div class="io-qreview-row"><strong>Correct answer:</strong> {correct_text}</div>'
                )
            if review.get("explanation_if_applicable"):
                rows.append(
                    f'<div class="io-qreview-row"><strong>Why:</strong> {review["explanation_if_applicable"]}</div>'
                )
        rows.append(
            f'<div class="io-qreview-row"><strong>What went well:</strong> {review.get("what_went_well", "")}</div>'
        )
        rows.append(
            f'<div class="io-qreview-row"><strong>What to improve:</strong> {review.get("what_to_improve", "")}</div>'
        )
        st.markdown(
            f'<div class="io-qreview">{"".join(rows)}</div>',
            unsafe_allow_html=True,
        )

    # Improved answer
    improved = feedback.get("improved_answer", {})
    st.markdown('<div class="io-section-title">Improved answer (rewrite)</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="io-muted"><strong>Question being rewritten:</strong> {improved.get("original_question", "")}</div>',
        unsafe_allow_html=True,
    )
    st.text_area(
        "Rewritten answer (copyable)",
        value=improved.get("rewrite", ""),
        height=160,
        key="improved_answer_text",
    )
    st.markdown(
        f'<div class="io-muted"><strong>What changed:</strong> {improved.get("what_changed", "")}</div>',
        unsafe_allow_html=True,
    )

    # Drills
    st.markdown('<div class="io-section-title">Targeted drills</div>', unsafe_allow_html=True)
    for drill in feedback.get("targeted_drills", []):
        st.markdown(
            f"""
            <div class="io-card">
                <h4>{drill.get('drill', '')}</h4>
                <p class="io-muted">Why this helps: {drill.get('why_this_helps', '')}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Drills summary as copyable text area
    drill_summary = "\n".join(
        f"- {d.get('drill', '')}\n    Why: {d.get('why_this_helps', '')}"
        for d in feedback.get("targeted_drills", [])
    )
    st.text_area(
        "Drills summary (copyable)",
        value=drill_summary,
        height=130,
        key="drills_summary_text",
    )

    st.markdown('<div class="io-section-title">Next practice question</div>', unsafe_allow_html=True)
    st.text_area(
        "Practice this next (copyable)",
        value=feedback.get("next_practice_question", ""),
        height=90,
        key="next_practice_text",
    )

    st.markdown(
        f"""
        <div class="io-card" style="background:#FFFBEB; border-color:#FCD34D;">
            <h4>Ethical reminder from the coach</h4>
            <p>{feedback.get("ethical_reminder", "")}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("Full transcript", expanded=False):
        st.markdown(
            f"<div class='io-muted'>{config['interview_type']} &middot; "
            f"{plan.get('resolved_mode', '?')} mode &middot; "
            f"{plan.get('resolved_difficulty', '?')} difficulty</div>",
            unsafe_allow_html=True,
        )
        for i, turn in enumerate(transcript, start=1):
            q = _question_obj(turn)
            st.markdown(f"**Q{i}** *(_{q.get('question_type', 'qualitative')}_)*: {q.get('question_text', '')}")
            if q.get("answer_format") == "multiple_choice_with_explanation":
                for c in q.get("choices", []):
                    st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;{c['label']}. {c['text']}")
                sel = _selected_choice(turn)
                st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;**Selected:** {sel or '(none)'}")
            st.markdown(f"> {_answer_text(turn)}")

    st.markdown(
        '<div class="io-section-title">Take it home / keep practicing</div>',
        unsafe_allow_html=True,
    )

    md_export = _build_markdown_export(config, plan, transcript, feedback)
    st.download_button(
        label="Download report (Markdown)",
        data=md_export,
        file_name="interviewos-report.md",
        mime="text/markdown",
        use_container_width=True,
        help="Save the full feedback dashboard, rewrite, and transcript as a Markdown file.",
    )

    current_diff = plan.get("resolved_difficulty", config.get("difficulty", "Intermediate"))
    if current_diff not in DIFFICULTY_LADDER:
        current_diff = "Intermediate"
    next_diff = _bump_difficulty(current_diff)
    if next_diff != current_diff:
        retry_label = f"Try again at {next_diff} difficulty (same opportunity)"
        retry_help = (
            f"Re-runs the interview at one notch higher difficulty "
            f"({current_diff} \u2192 {next_diff}) with the same opportunity "
            "and background."
        )
    else:
        retry_label = "Try again at Intense difficulty (same opportunity)"
        retry_help = "Re-runs the interview at the same difficulty (already at Intense)."

    if st.button(retry_label, use_container_width=True, help=retry_help):
        new_config = {**config, "difficulty": next_diff}
        st.session_state.config = new_config
        st.session_state.transcript = []
        st.session_state.feedback = None
        st.session_state.interview_complete = False
        st.session_state.question_index = 0
        st.session_state.current_question_note = ""
        with st.spinner("Re-planning the interview..."):
            new_plan = plan_interview(new_config)
        st.session_state.interview_plan = new_plan
        with st.spinner("Generating your first question..."):
            q = start_interview(new_config, new_plan)
        st.session_state.current_question = q
        st.session_state.current_question_note = q.get("interviewer_note", "")
        st.session_state.question_start_time = time.time()
        st.session_state.interview_started = True
        st.rerun()

    st.write("")
    if st.button("Start over", type="primary"):
        reset_interview()
        st.rerun()


def render_ethics_footer() -> None:
    st.markdown('<div class="io-section-title">Ethical safeguards</div>', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="io-card">
            <ul>
                <li>InterviewOS is <strong>coaching</strong>, not a hiring or admissions decision.</li>
                <li>It does not predict whether you will get a role.</li>
                <li>It should not pressure you to erase your voice, identity, accent, dialect, or background.</li>
                <li>It should not invent achievements you did not mention.</li>
                <li>For technical questions, it can make math or correctness mistakes &mdash;
                    verify explanations against a textbook, problem set, or trusted human before relying on them.</li>
                <li>Feedback reflects one simulated interviewer, not objective truth.</li>
                <li><strong>You remain in control.</strong></li>
            </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    st.set_page_config(
        page_title="InterviewOS",
        page_icon="🎯",
        layout="centered",
        initial_sidebar_state="collapsed",
    )
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    _init_state()

    render_hero()
    render_intro_cards()
    st.divider()

    if not st.session_state.interview_started:
        render_setup()
    elif not st.session_state.interview_complete:
        render_interview()
    else:
        render_feedback()

    st.divider()
    render_ethics_footer()
    st.markdown(
        '<div class="io-muted" style="text-align:center; margin-top:1rem;">'
        "InterviewOS &middot; Built for the Spring Sprint Hackathon &middot; "
        "Economic Empowerment & Education track"
        "</div>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
