from __future__ import annotations

import re
import uuid

from interviewos.banks import (
    PROBE_TEMPLATES,
    qualitative_starter,
    select_technical_item,
)
from interviewos.constants import HEDGE_PATTERN
from interviewos.models import Answer, InterviewConfig, InterviewPlan, Question, Turn


def diagnose_answer(answer: str) -> str:
    text = (answer or "").strip()
    words = text.split()
    if len(words) < 12:
        return "vague"
    if not re.search(r"\d|project|built|wrote|made|led|won|class|course|lab", text, re.I):
        return "no_evidence"
    if not re.search(
        r"because|so that|in order to|matters|care|excited|interested", text, re.I
    ):
        return "no_motivation"
    if len(words) > 70:
        return "strong"
    return "ok"


def quote_phrase(text: str, limit: int = 8) -> str:
    cleaned = re.sub(r"\s+", " ", (text or "").strip())
    if not cleaned:
        return "your last answer"
    words = cleaned.split()
    snippet = " ".join(words[:limit]).strip(".,;:!?")
    return snippet or "your last answer"


def new_question_id() -> str:
    return str(uuid.uuid4())


def make_qualitative_question(
    config: InterviewConfig,
    plan: InterviewPlan,
    *,
    action: str,
    quoted_phrase: str | None = None,
    diagnosis: str | None = None,
) -> Question:
    difficulty = plan.resolved_difficulty
    if action == "probe_previous":
        key = diagnosis if diagnosis in PROBE_TEMPLATES else "vague"
        text, note = PROBE_TEMPLATES[key]
        if quoted_phrase and key != "technical_miss":
            text = (
                f'You said “{quoted_phrase}.” {text}'
            )
        return Question(
            id=new_question_id(),
            question_text=text,
            question_type="qualitative",
            answer_format="free_response",
            interviewer_note=note,
            action="probe_previous",
            quoted_phrase=quoted_phrase,
            difficulty=difficulty,
        )
    stem = qualitative_starter(config.interview_type, difficulty)
    return Question(
        id=new_question_id(),
        question_text=stem,
        question_type="qualitative",
        answer_format="free_response",
        interviewer_note="Opening or continuing a behavioral thread.",
        action="ask_qualitative",
        difficulty=difficulty,
    )


def make_technical_question(
    config: InterviewConfig,
    plan: InterviewPlan,
    used_stems: set[str],
    *,
    action: str = "ask_technical",
    prefer_format: str | None = None,
    quoted_phrase: str | None = None,
) -> Question:
    item = select_technical_item(
        config.interview_type,
        plan.resolved_difficulty,
        used_stems,
        prefer_format=prefer_format,
    )
    return Question(
        id=new_question_id(),
        question_text=item["question_text"],
        question_type="technical",
        answer_format=item["answer_format"],
        choices=item.get("choices") or [],
        latex=item.get("latex"),
        snippet=item.get("snippet"),
        interviewer_note=item.get("interviewer_note") or "",
        action=action,  # type: ignore[arg-type]
        quoted_phrase=quoted_phrase,
        difficulty=item["difficulty"],
        correct_label=item.get("correct_label"),
        correct_explanation=item.get("correct_explanation"),
    )


def make_technical_probe(last: Turn) -> Question:
    phrase = quote_phrase(last.answer.written_response or last.answer.selected_choice or "")
    text, note = PROBE_TEMPLATES["technical_miss"]
    return Question(
        id=new_question_id(),
        question_text=f'You picked {last.answer.selected_choice or "nothing"}. {text}',
        question_type="technical",
        answer_format="explain_snippet",
        snippet=last.question.question_text,
        interviewer_note=note,
        action="probe_previous",
        quoted_phrase=phrase,
        difficulty=last.question.difficulty,
        correct_label=None,
        correct_explanation=last.question.correct_explanation,
    )


def choose_action(
    plan: InterviewPlan,
    turns: list[Turn],
) -> str:
    n = plan.resolved_question_count
    idx = len(turns)
    remaining = n - idx
    if remaining <= 0:
        return "wrap_up"

    mode = plan.resolved_mode
    last = turns[-1] if turns else None
    tech_count = sum(1 for t in turns if t.question.question_type == "technical")
    last_was_probe = bool(last and last.question.action == "probe_previous")

    if last and not last_was_probe:
        if last.question.question_type == "qualitative":
            diagnosis = diagnose_answer(last.answer.written_response)
            if diagnosis in {"vague", "no_evidence"} and remaining >= 1:
                if mode == "Mixed" and remaining == 1 and tech_count == 0:
                    return "ask_technical"
                if mode in {"Qualitative", "Mixed"}:
                    return "probe_previous"
        if last.question.question_type == "technical" and mode in {"Technical", "Mixed"}:
            key = last.question.correct_label
            picked = last.answer.selected_choice
            if key and picked and picked != key and remaining >= 1:
                if mode == "Mixed" and remaining == 1:
                    qual_count = len(turns) - tech_count
                    if qual_count == 0:
                        return "ask_qualitative"
                return "probe_previous"

    if mode == "Qualitative":
        return "ask_qualitative"
    if mode == "Technical":
        return "ask_technical"

    # Mixed: alternate, qualitative first, unless a probe just happened.
    if last_was_probe and last:
        if last.question.question_type == "qualitative":
            return "ask_technical"
        return "ask_qualitative"
    if tech_count >= (idx + 1) / 2:
        return "ask_qualitative"
    if idx % 2 == 0:
        return "ask_qualitative"
    return "ask_technical"


def generate_question(
    config: InterviewConfig,
    plan: InterviewPlan,
    turns: list[Turn],
    used_stems: set[str],
    *,
    live: bool = False,
    messages: list[dict[str, str]] | None = None,
) -> Question:
    action = choose_action(plan, turns)
    if action == "wrap_up":
        raise RuntimeError("interview already complete")

    last = turns[-1] if turns else None
    if live:
        try:
            from interviewos.claude import next_question_live

            return next_question_live(
                config,
                plan,
                messages or [],
                action,
                new_question_id(),
            )
        except Exception:
            pass

    if action == "probe_previous" and last:
        if last.question.question_type == "technical":
            return make_technical_probe(last)
        diagnosis = diagnose_answer(last.answer.written_response)
        return make_qualitative_question(
            config,
            plan,
            action="probe_previous",
            quoted_phrase=quote_phrase(last.answer.written_response),
            diagnosis=diagnosis,
        )
    if action == "ask_technical":
        prefer = None
        # Alternate MCQ warmup with explain-snippet when possible.
        tech_turns = [t for t in turns if t.question.question_type == "technical"]
        if tech_turns and tech_turns[-1].question.answer_format == "multiple_choice_with_explanation":
            prefer = "explain_snippet"
        elif not tech_turns:
            prefer = "multiple_choice_with_explanation"
        return make_technical_question(
            config, plan, used_stems, action="ask_technical", prefer_format=prefer
        )
    return make_qualitative_question(config, plan, action="ask_qualitative")


def hedge_density(text: str) -> float:
    words = (text or "").split()
    if not words:
        return 0.0
    return len(HEDGE_PATTERN.findall(text)) / max(len(words), 1) * 100
