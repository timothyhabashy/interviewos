"""Golden demo-mode interview: deterministic, no network."""

from interviewos.constants import SAMPLES
from interviewos.engine import InterviewEngine
from interviewos.models import Answer, InterviewConfig
from interviewos.public import assert_no_secrets, public_question_dict


def test_golden_research_assistant_demo_session():
    sample = SAMPLES["research_assistant"]
    config = InterviewConfig(
        interview_type=sample["interview_type"],
        interview_mode=sample["interview_mode"],
        difficulty=sample["difficulty"],
        question_count=sample["question_count"],
        timer_seconds=sample["timer_seconds"],
        opportunity_description=sample["opportunity_description"],
        applicant_background=sample["applicant_background"],
    )
    engine = InterviewEngine(config, live=False)
    assert engine.plan.resolved_mode == "Mixed"
    assert engine.plan.resolved_difficulty == "Intermediate"
    assert engine.plan.resolved_question_count == 3

    q1 = engine.start()
    assert q1.question_type == "qualitative"
    assert_no_secrets(q1.model_dump())

    q2 = engine.submit(
        Answer(
            written_response=(
                "Last semester I built a Monte Carlo option pricing simulator in Python "
                "because I wanted to see how randomness can model real systems. I learned "
                "about NumPy and how to debug a simulation that returns plausible-but-wrong numbers."
            )
        )
    )
    assert q2 is not None
    assert q2.question_type == "technical"
    public = public_question_dict(engine.pending_question)  # type: ignore[arg-type]
    assert_no_secrets(public)
    if q2.answer_format == "multiple_choice_with_explanation":
        assert engine.secrets[q2.id].correct_label

    choice = q2.choices[0].label if q2.choices else None
    q3 = engine.submit(
        Answer(
            selected_choice=choice,
            written_response="I picked this because standard error should shrink as I add paths.",
        )
    )
    assert q3 is not None
    q_end = engine.submit(
        Answer(
            written_response=(
                "I come from a school where research was not really an option. "
                "A summer alongside people who do this professionally would let me "
                "figure out if I actually want to pursue it."
            )
        )
    )
    assert q_end is None
    feedback = engine.complete()
    assert 0 <= feedback.overall_score <= 100
    assert len(feedback.question_reviews) == 3
    assert feedback.assessed_dimension_count >= 8
    assert feedback.improved_answer.rewrite
    assert len(feedback.targeted_drills) == 3
