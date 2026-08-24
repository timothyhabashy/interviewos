from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from interviewos.constants import MAX_QUESTION_COUNT

QuestionType = Literal["qualitative", "technical"]
AnswerFormat = Literal[
    "free_response",
    "multiple_choice_with_explanation",
    "explain_snippet",
]
InterviewerAction = Literal[
    "ask_qualitative",
    "ask_technical",
    "probe_previous",
    "wrap_up",
]
AnswerSource = Literal["text", "voice"]
SessionStatus = Literal["ready", "in_progress", "awaiting_score", "complete"]


class InterviewConfig(BaseModel):
    interview_type: str
    interview_mode: str = "Auto"
    difficulty: str = "Auto"
    question_count: int | None = None
    timer_seconds: int | None = None
    opportunity_description: str = ""
    applicant_background: str = ""


class InterviewPlan(BaseModel):
    resolved_mode: str
    resolved_difficulty: str
    resolved_question_count: int = Field(ge=1, le=MAX_QUESTION_COUNT)
    resolved_timer_seconds: int | None = None
    rationale: str = ""
    question_style_notes: str = ""


class QuestionChoice(BaseModel):
    label: str
    text: str


class Question(BaseModel):
    id: str
    question_text: str
    question_type: QuestionType = "qualitative"
    answer_format: AnswerFormat = "free_response"
    choices: list[QuestionChoice] = Field(default_factory=list)
    latex: str | None = None
    snippet: str | None = None
    interviewer_note: str = ""
    action: InterviewerAction = "ask_qualitative"
    quoted_phrase: str | None = None
    difficulty: str = "Intermediate"
    # Server-only. Stripped before any public payload.
    correct_label: str | None = None
    correct_explanation: str | None = None


class QuestionSecret(BaseModel):
    question_id: str
    correct_label: str | None = None
    correct_explanation: str | None = None


class PublicQuestion(BaseModel):
    id: str
    question_text: str
    question_type: QuestionType
    answer_format: AnswerFormat
    choices: list[QuestionChoice] = Field(default_factory=list)
    latex: str | None = None
    snippet: str | None = None
    interviewer_note: str = ""
    action: InterviewerAction
    quoted_phrase: str | None = None
    difficulty: str


class Answer(BaseModel):
    selected_choice: str | None = None
    written_response: str = ""
    time_expired: bool = False
    source: AnswerSource = "text"


class Turn(BaseModel):
    question: Question
    answer: Answer


class RubricItem(BaseModel):
    score: int | None = Field(default=None, ge=1, le=5)
    feedback: str
    assessed: bool = True


class QuestionReview(BaseModel):
    question_index: int
    question_id: str
    question_type: str
    what_went_well: str
    what_to_improve: str
    correct_answer_if_applicable: str | None = None
    explanation_if_applicable: str | None = None
    time_expired: bool = False
    source: AnswerSource = "text"


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
    coaching_notes: list[str] = Field(default_factory=list)
    assessed_dimension_count: int = 0


class EngineState(BaseModel):
    config: InterviewConfig
    plan: InterviewPlan
    turns: list[Turn] = Field(default_factory=list)
    messages: list[dict[str, Any]] = Field(default_factory=list)
    used_stems: list[str] = Field(default_factory=list)
    pending_question: Question | None = None
    status: SessionStatus = "ready"
    secrets: dict[str, QuestionSecret] = Field(default_factory=dict)
