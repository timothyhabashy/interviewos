from __future__ import annotations

from interviewos.models import PublicQuestion, Question, QuestionSecret

SECRET_FIELDS = ("correct_label", "correct_explanation")


def extract_secret(question: Question) -> QuestionSecret | None:
    if not question.correct_label and not question.correct_explanation:
        return None
    return QuestionSecret(
        question_id=question.id,
        correct_label=question.correct_label,
        correct_explanation=question.correct_explanation,
    )


def to_public_question(question: Question) -> PublicQuestion:
    return PublicQuestion(
        id=question.id,
        question_text=question.question_text,
        question_type=question.question_type,
        answer_format=question.answer_format,
        choices=list(question.choices),
        latex=question.latex,
        snippet=question.snippet,
        interviewer_note=question.interviewer_note,
        action=question.action,
        quoted_phrase=question.quoted_phrase,
        difficulty=question.difficulty,
    )


def public_question_dict(question: Question) -> dict:
    data = to_public_question(question).model_dump()
    for field in SECRET_FIELDS:
        data.pop(field, None)
    return data


def assert_no_secrets(payload: dict) -> None:
    blob = _flatten_keys(payload)
    for field in SECRET_FIELDS:
        if field in blob:
            raise AssertionError(f"secret field leaked: {field}")


def _flatten_keys(value: object, acc: set[str] | None = None) -> set[str]:
    keys: set[str] = acc if acc is not None else set()
    if isinstance(value, dict):
        for k, v in value.items():
            keys.add(str(k))
            _flatten_keys(v, keys)
    elif isinstance(value, list):
        for item in value:
            _flatten_keys(item, keys)
    return keys
