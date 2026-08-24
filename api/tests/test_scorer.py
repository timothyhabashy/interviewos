from interviewos.engine import InterviewEngine
from interviewos.models import (
    Answer,
    InterviewConfig,
    InterviewPlan,
    Question,
    RubricItem,
    Turn,
)
from interviewos.scorer import mock_feedback, overall_score


def test_overall_score_ignores_na_dimensions():
    rubric = {
        "clarity": RubricItem(score=5, feedback="ok", assessed=True),
        "technical_correctness": RubricItem(
            score=None, feedback="n/a", assessed=False
        ),
    }
    score, assessed = overall_score(rubric)
    assert assessed == 1
    assert score == 100


def test_qualitative_only_does_not_average_fake_technical_threes():
    engine = InterviewEngine(
        InterviewConfig(
            interview_type="Scholarship",
            interview_mode="Qualitative",
            difficulty="Beginner",
            question_count=2,
        ),
        live=False,
    )
    engine.start()
    engine.submit(
        Answer(
            written_response=(
                "I built a tutoring program at my community college because I wanted "
                "first-gen students to have somewhere to go. I learned that showing up "
                "every week mattered more than a perfect lesson plan."
            )
        )
    )
    engine.submit(
        Answer(
            written_response=(
                "This scholarship would cut my work hours so I can take organic chemistry "
                "lab. Without it I stay closing shift four nights a week."
            )
        )
    )
    feedback = engine.complete()
    assert feedback.rubric["technical_correctness"].assessed is False
    assert feedback.rubric["technical_correctness"].score is None
    assert feedback.assessed_dimension_count == 8
    # Old scorer stuffed 3/5 on unused dims and pulled the mean down.
    assert feedback.overall_score > 40


def test_rewrite_does_not_invent_achievements():
    plan = InterviewPlan(
        resolved_mode="Qualitative",
        resolved_difficulty="Beginner",
        resolved_question_count=1,
    )
    turn = Turn(
        question=Question(
            id="q1",
            question_text="Why this role?",
            question_type="qualitative",
        ),
        answer=Answer(written_response="I guess I just maybe want to learn."),
    )
    feedback = mock_feedback(
        InterviewConfig(interview_type="Internship", opportunity_description="Summer internship."),
        plan,
        [turn],
    )
    rewrite = feedback.improved_answer.rewrite.lower()
    assert "published" not in rewrite
    assert "i guess" not in rewrite
    assert "invent" in feedback.improved_answer.what_changed.lower() or "no new" in feedback.improved_answer.what_changed.lower()


def test_timer_overrun_becomes_coaching_note():
    plan = InterviewPlan(
        resolved_mode="Qualitative",
        resolved_difficulty="Beginner",
        resolved_question_count=1,
    )
    turn = Turn(
        question=Question(
            id="q1",
            question_text="Tell me about yourself.",
            question_type="qualitative",
        ),
        answer=Answer(
            written_response="I built a robot in class and learned to debug it.",
            time_expired=True,
        ),
    )
    feedback = mock_feedback(InterviewConfig(interview_type="Internship"), plan, [turn])
    assert feedback.question_reviews[0].time_expired is True
    assert any("timer" in note.lower() for note in feedback.coaching_notes)


def test_mcq_graded_against_stored_key():
    plan = InterviewPlan(
        resolved_mode="Technical",
        resolved_difficulty="Beginner",
        resolved_question_count=1,
    )
    turn = Turn(
        question=Question(
            id="q1",
            question_text="Binary search complexity?",
            question_type="technical",
            answer_format="multiple_choice_with_explanation",
            choices=[
                {"label": "A", "text": "O(1)"},
                {"label": "B", "text": "O(log n)"},
            ],
            correct_label="B",
            correct_explanation="Halving.",
        ),
        answer=Answer(selected_choice="A", written_response="I counted steps and guessed linear."),
    )
    feedback = mock_feedback(InterviewConfig(interview_type="Technical SWE"), plan, [turn])
    review = feedback.question_reviews[0]
    assert review.correct_answer_if_applicable
    assert review.correct_answer_if_applicable.startswith("B.")
    assert "A" in review.what_to_improve or "correct" in review.what_to_improve.lower()


def test_authenticity_can_be_below_four():
    plan = InterviewPlan(
        resolved_mode="Qualitative",
        resolved_difficulty="Beginner",
        resolved_question_count=1,
    )
    turn = Turn(
        question=Question(id="q1", question_text="Why?", question_type="qualitative"),
        answer=Answer(written_response="ok"),
    )
    feedback = mock_feedback(InterviewConfig(interview_type="Internship"), plan, [turn])
    assert feedback.rubric["authenticity"].score is not None
    assert feedback.rubric["authenticity"].score < 4
