import os

import pytest

from interviewos.constants import has_api_key
from interviewos.models import InterviewConfig
from interviewos.planner import plan_interview


@pytest.mark.skipif(not has_api_key(), reason="ANTHROPIC_API_KEY not set")
def test_live_planner_optional():
    plan = plan_interview(
        InterviewConfig(
            interview_type="Internship",
            interview_mode="Qualitative",
            difficulty="Beginner",
            question_count=3,
        ),
        live=True,
    )
    assert plan.resolved_mode == "Qualitative"
    assert plan.resolved_difficulty == "Beginner"
    assert plan.resolved_question_count == 3
