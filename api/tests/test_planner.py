from interviewos.constants import STEM_TYPES
from interviewos.models import InterviewConfig
from interviewos.planner import mock_plan_interview, plan_interview


def test_planner_respects_non_auto_choices():
    config = InterviewConfig(
        interview_type="Internship",
        interview_mode="Qualitative",
        difficulty="Intense",
        question_count=7,
        timer_seconds=45,
    )
    plan = plan_interview(config, live=False)
    assert plan.resolved_mode == "Qualitative"
    assert plan.resolved_difficulty == "Intense"
    assert plan.resolved_question_count == 7
    assert plan.resolved_timer_seconds == 45


def test_auto_stem_type_becomes_mixed():
    config = InterviewConfig(
        interview_type="Technical SWE",
        interview_mode="Auto",
        difficulty="Auto",
    )
    plan = mock_plan_interview(config)
    assert plan.resolved_mode == "Mixed"
    assert config.interview_type in STEM_TYPES


def test_auto_difficulty_from_background():
    beginner = mock_plan_interview(
        InterviewConfig(
            interview_type="Internship",
            interview_mode="Auto",
            difficulty="Auto",
            applicant_background="I am a beginner with no experience.",
        )
    )
    assert beginner.resolved_difficulty == "Beginner"

    advanced = mock_plan_interview(
        InterviewConfig(
            interview_type="Internship",
            interview_mode="Auto",
            difficulty="Auto",
            applicant_background="PhD student, senior researcher.",
        )
    )
    assert advanced.resolved_difficulty == "Advanced"


def test_auto_count_increases_at_advanced():
    plan = mock_plan_interview(
        InterviewConfig(
            interview_type="Technical SWE",
            interview_mode="Technical",
            difficulty="Advanced",
            question_count=None,
        )
    )
    assert plan.resolved_question_count == 5
