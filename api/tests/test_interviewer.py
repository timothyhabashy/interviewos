from interviewos.engine import InterviewEngine
from interviewos.interviewer import choose_action, diagnose_answer
from interviewos.models import Answer, InterviewConfig, InterviewPlan, Question, Turn
from interviewos.public import assert_no_secrets, public_question_dict


def _config(**kwargs) -> InterviewConfig:
    base = dict(
        interview_type="Research Program",
        interview_mode="Mixed",
        difficulty="Intermediate",
        question_count=3,
        timer_seconds=90,
        opportunity_description="Summer research in scientific computing.",
        applicant_background="First-year student who built a Monte Carlo project.",
    )
    base.update(kwargs)
    return InterviewConfig(**base)


def test_mixed_mode_emits_probe_after_vague_answer():
    engine = InterviewEngine(_config(), live=False)
    first = engine.start()
    assert first.question_type == "qualitative"
    nxt = engine.submit(Answer(written_response="Not sure."))
    assert nxt is not None
    assert nxt.action == "probe_previous"
    assert nxt.quoted_phrase


def test_technical_mcq_persists_server_side_key():
    engine = InterviewEngine(
        _config(interview_mode="Technical", interview_type="Technical SWE"),
        live=False,
    )
    q = engine.start()
    public = public_question_dict(engine.pending_question)  # type: ignore[arg-type]
    assert_no_secrets(public)
    assert q.id in engine.secrets
    secret = engine.secrets[q.id]
    if q.answer_format == "multiple_choice_with_explanation":
        assert secret.correct_label
        assert secret.correct_explanation


def test_public_question_strips_keys():
    engine = InterviewEngine(
        _config(interview_mode="Technical", interview_type="Data Science"),
        live=False,
    )
    engine.start()
    dumped = engine.dump_state().pending_question
    assert dumped is not None
    public = public_question_dict(dumped)
    assert "correct_label" not in public
    assert "correct_explanation" not in public


def test_choose_action_wraps_up_when_full():
    plan = InterviewPlan(
        resolved_mode="Qualitative",
        resolved_difficulty="Beginner",
        resolved_question_count=1,
    )
    q = Question(
        id="q1",
        question_text="Tell me about yourself.",
        question_type="qualitative",
        answer_format="free_response",
    )
    turns = [Turn(question=q, answer=Answer(written_response="I built a robot for class."))]
    assert choose_action(plan, turns) == "wrap_up"


def test_diagnose_vague():
    assert diagnose_answer("ok") == "vague"


def test_engine_roundtrip_state():
    engine = InterviewEngine(_config(interview_mode="Qualitative"), live=False)
    engine.start()
    engine.submit(Answer(written_response="I built a weather dashboard in Python because I care about climate data."))
    state = engine.dump_state()
    restored = InterviewEngine.load_state(state, live=False)
    assert restored.plan.resolved_question_count == engine.plan.resolved_question_count
    assert len(restored.turns) == 1
    assert restored.pending_question is not None
