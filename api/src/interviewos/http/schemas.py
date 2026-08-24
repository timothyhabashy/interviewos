from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from interviewos.models import Answer, Feedback, InterviewConfig, InterviewPlan, PublicQuestion


class CreateSessionRequest(BaseModel):
    interview_type: str
    interview_mode: str = "Auto"
    difficulty: str = "Auto"
    question_count: int | None = None
    timer_seconds: int | None = None
    opportunity_description: str = ""
    applicant_background: str = ""


class SessionCreated(BaseModel):
    id: str
    status: str
    plan: InterviewPlan
    question: PublicQuestion
    live: bool


class SessionView(BaseModel):
    id: str
    status: str
    plan: InterviewPlan
    config: InterviewConfig
    question: PublicQuestion | None = None
    answered_count: int = 0
    owner_id: str | None = None


class SubmitTurnRequest(BaseModel):
    written_response: str = ""
    selected_choice: str | None = None
    time_expired: bool = False
    source: Literal["text", "voice"] = "text"


class SubmitTurnResponse(BaseModel):
    id: str
    status: str
    question: PublicQuestion | None = None
    answered_count: int


class CompleteResponse(BaseModel):
    id: str
    status: str
    report: Feedback


class HistoryItem(BaseModel):
    id: str
    status: str
    interview_type: str
    difficulty: str
    mode: str
    overall_score: int | None = None
    created_at: str


class CompareResponse(BaseModel):
    left: dict[str, Any]
    right: dict[str, Any]


class MetaResponse(BaseModel):
    interview_types: list[str]
    interview_modes: list[str]
    difficulty_levels: list[str]
    samples: dict[str, Any]
    live: bool
