from __future__ import annotations

import json
import os
import re
from typing import Any

from pydantic import ValidationError

from interviewos.constants import ETHICAL_GUARDRAILS, model_name
from interviewos.models import InterviewConfig, InterviewPlan, Question
from interviewos.planner import plan_system_prompt


def _extract_json(text: str) -> dict[str, Any]:
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


def call_claude_json(
    system_prompt: str,
    user_prompt: str,
    *,
    messages: list[dict[str, str]] | None = None,
    max_tokens: int = 4000,
) -> dict[str, Any]:
    from anthropic import Anthropic

    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    convo = list(messages or [])
    convo.append({"role": "user", "content": user_prompt})
    message = client.messages.create(
        model=model_name(),
        max_tokens=max_tokens,
        system=(
            system_prompt
            + "\n\nReturn ONLY a single valid JSON object. No prose. No markdown. No code fences."
        ),
        messages=convo,
    )
    text_parts = [
        block.text for block in message.content if getattr(block, "type", "") == "text"
    ]
    raw = "".join(text_parts).strip()
    return _extract_json(raw)


def plan_interview_live(config: InterviewConfig) -> InterviewPlan:
    user = (
        "User selections (Auto means infer):\n"
        f"- Interview mode: {config.interview_mode}\n"
        f"- Difficulty: {config.difficulty}\n"
        f"- Question count: {config.question_count or 'Auto'}\n"
        f"- Timer (seconds/question): {config.timer_seconds or 'Off'}\n"
        f"- Interview type: {config.interview_type}\n"
        f"- Opportunity description: {(config.opportunity_description or '(none)').strip()}\n"
        f"- Applicant background: {(config.applicant_background or '(none)').strip()}\n\n"
        "Return JSON with keys: resolved_mode, resolved_difficulty, "
        "resolved_question_count, resolved_timer_seconds, rationale, "
        "question_style_notes."
    )
    data = call_claude_json(plan_system_prompt(), user, max_tokens=1200)
    return InterviewPlan(**data)


def next_question_live(
    config: InterviewConfig,
    plan: InterviewPlan,
    messages: list[dict[str, str]],
    desired_action: str,
    question_id: str,
) -> Question:
    system = (
        ETHICAL_GUARDRAILS
        + "\nYou are a live interviewer. Stay in character.\n"
        "If desired_action is probe_previous, you MUST quote a short phrase from the last answer.\n"
        "For technical multiple choice, include correct_label and correct_explanation "
        "for the server-side answer key. The candidate will not see those fields.\n"
        "Return JSON:\n"
        "{\n"
        '  "question_text": string,\n'
        '  "question_type": "qualitative"|"technical",\n'
        '  "answer_format": "free_response"|"multiple_choice_with_explanation"|"explain_snippet",\n'
        '  "choices": [{"label":"A","text":string},...],\n'
        '  "latex": string|null,\n'
        '  "snippet": string|null,\n'
        '  "interviewer_note": string,\n'
        '  "quoted_phrase": string|null,\n'
        '  "correct_label": string|null,\n'
        '  "correct_explanation": string|null\n'
        "}"
    )
    user = (
        f"Desired action: {desired_action}\n"
        f"Difficulty: {plan.resolved_difficulty}\n"
        f"Mode: {plan.resolved_mode}\n"
        f"Interview type: {config.interview_type}\n"
        f"Opportunity: {config.opportunity_description or '(none)'}\n"
        f"Background: {config.applicant_background or '(none)'}\n"
        f"Style notes: {plan.question_style_notes}\n"
        "Generate the next question now."
    )
    data = call_claude_json(system, user, messages=messages, max_tokens=2000)
    qtype = data.get("question_type") or (
        "technical" if desired_action == "ask_technical" else "qualitative"
    )
    fmt = data.get("answer_format")
    if qtype == "qualitative":
        fmt = "free_response"
        data["choices"] = []
        data["correct_label"] = None
    elif fmt not in {"multiple_choice_with_explanation", "explain_snippet"}:
        fmt = "multiple_choice_with_explanation"
    if fmt == "multiple_choice_with_explanation":
        choices = data.get("choices") or []
        cleaned = []
        for c in choices[:4]:
            if isinstance(c, dict) and "label" in c and "text" in c:
                cleaned.append({"label": str(c["label"]).strip(), "text": str(c["text"])})
        if len(cleaned) != 4 or not data.get("correct_label"):
            raise ValueError("live technical MCQ missing choices or correct_label")
        data["choices"] = cleaned
    action = desired_action if desired_action != "wrap_up" else "ask_qualitative"
    return Question(
        id=question_id,
        question_text=str(data["question_text"]),
        question_type=qtype,
        answer_format=fmt,
        choices=data.get("choices") or [],
        latex=data.get("latex"),
        snippet=data.get("snippet"),
        interviewer_note=str(data.get("interviewer_note") or ""),
        action=action,  # type: ignore[arg-type]
        quoted_phrase=data.get("quoted_phrase"),
        difficulty=plan.resolved_difficulty,
        correct_label=data.get("correct_label"),
        correct_explanation=data.get("correct_explanation"),
    )


def score_interview_live(user_prompt: str) -> dict[str, Any]:
    system = (
        ETHICAL_GUARDRAILS
        + "\nScore a mock interview. Two-pass: first judge each question, then the rubric.\n"
        "Omit unassessed dimensions by setting assessed=false and score=null.\n"
        "Do not invent achievements. Grade technical MCQs against the provided answer key.\n"
        "Return JSON matching the Feedback schema."
    )
    return call_claude_json(system, user_prompt, max_tokens=6000)
