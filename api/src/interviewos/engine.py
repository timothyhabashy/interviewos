from __future__ import annotations

from interviewos.interviewer import generate_question
from interviewos.models import (
    Answer,
    EngineState,
    Feedback,
    InterviewConfig,
    InterviewPlan,
    PublicQuestion,
    Question,
    QuestionSecret,
    Turn,
)
from interviewos.planner import plan_interview
from interviewos.public import extract_secret, to_public_question
from interviewos.scorer import score_interview


class InterviewEngine:
    """In-memory interview session: one conversation, not N isolated prompts."""

    def __init__(
        self,
        config: InterviewConfig,
        *,
        live: bool = False,
        plan: InterviewPlan | None = None,
    ) -> None:
        self.config = config
        self.live = live
        self.plan = plan or plan_interview(config, live=live)
        self.turns: list[Turn] = []
        self.messages: list[dict[str, str]] = []
        self.used_stems: set[str] = set()
        self.pending_question: Question | None = None
        self.status = "ready"
        self.secrets: dict[str, QuestionSecret] = {}

    def start(self) -> PublicQuestion:
        question = generate_question(
            self.config,
            self.plan,
            self.turns,
            self.used_stems,
            live=self.live,
            messages=self.messages,
        )
        self._arm(question)
        self.status = "in_progress"
        return to_public_question(question)

    def submit(self, answer: Answer) -> PublicQuestion | None:
        if self.pending_question is None:
            raise RuntimeError("no pending question")
        question = self.pending_question
        self.turns.append(Turn(question=question, answer=answer))
        self.messages.append(
            {
                "role": "assistant",
                "content": question.question_text,
            }
        )
        self.messages.append(
            {
                "role": "user",
                "content": self._format_answer(answer),
            }
        )
        self.pending_question = None
        if len(self.turns) >= self.plan.resolved_question_count:
            self.status = "awaiting_score"
            return None
        nxt = generate_question(
            self.config,
            self.plan,
            self.turns,
            self.used_stems,
            live=self.live,
            messages=self.messages,
        )
        self._arm(nxt)
        return to_public_question(nxt)

    def complete(self) -> Feedback:
        if not self.turns:
            raise RuntimeError("cannot score an empty interview")
        feedback = score_interview(
            self.config, self.plan, self.turns, live=self.live
        )
        self.status = "complete"
        return feedback

    def current_public_question(self) -> PublicQuestion | None:
        if self.pending_question is None:
            return None
        return to_public_question(self.pending_question)

    def dump_state(self) -> EngineState:
        return EngineState(
            config=self.config,
            plan=self.plan,
            turns=self.turns,
            messages=self.messages,
            used_stems=sorted(self.used_stems),
            pending_question=self.pending_question,
            status=self.status,  # type: ignore[arg-type]
            secrets=self.secrets,
        )

    @classmethod
    def load_state(cls, state: EngineState, *, live: bool = False) -> InterviewEngine:
        engine = cls(state.config, live=live, plan=state.plan)
        engine.turns = list(state.turns)
        engine.messages = list(state.messages)
        engine.used_stems = set(state.used_stems)
        engine.pending_question = state.pending_question
        engine.status = state.status
        engine.secrets = dict(state.secrets)
        return engine

    def _arm(self, question: Question) -> None:
        self.pending_question = question
        self.used_stems.add(question.question_text)
        secret = extract_secret(question)
        if secret:
            self.secrets[question.id] = secret

    @staticmethod
    def _format_answer(answer: Answer) -> str:
        bits = []
        if answer.selected_choice:
            bits.append(f"Selected: {answer.selected_choice}")
        bits.append(answer.written_response)
        if answer.time_expired:
            bits.append("[timer expired]")
        if answer.source == "voice":
            bits.append("[answered by voice]")
        return "\n".join(bits)
