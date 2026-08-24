from __future__ import annotations

import uuid

from sqlalchemy.orm import Session as DbSession

from interviewos.engine import InterviewEngine
from interviewos.http.db import QuestionSecretRow, ReportRow, SessionRow, TurnRow, UserRow
from interviewos.models import EngineState
from interviewos.public import public_question_dict


def persist_engine(db: DbSession, row: SessionRow, engine: InterviewEngine) -> None:
    state = engine.dump_state()
    row.engine_state = state.model_dump(mode="json")
    row.status = engine.status
    for qid, secret in engine.secrets.items():
        existing = db.get(QuestionSecretRow, qid)
        if existing is None:
            db.add(
                QuestionSecretRow(
                    question_id=qid,
                    session_id=row.id,
                    correct_label=secret.correct_label,
                    correct_explanation=secret.correct_explanation,
                )
            )
    db.add(row)


def load_engine(row: SessionRow, *, live: bool) -> InterviewEngine:
    state = EngineState.model_validate(row.engine_state)
    return InterviewEngine.load_state(state, live=live)


def record_turn(db: DbSession, session_id: str, engine: InterviewEngine) -> None:
    if not engine.turns:
        return
    last = engine.turns[-1]
    db.add(
        TurnRow(
            session_id=session_id,
            question_id=last.question.id,
            question_public=public_question_dict(last.question),
            answer=last.answer.model_dump(mode="json"),
        )
    )


def ensure_user(db: DbSession, user_id: str) -> UserRow:
    row = db.get(UserRow, user_id)
    if row is None:
        row = UserRow(id=user_id, clerk_subject=user_id)
        db.add(row)
        db.flush()
    return row


def new_session_id() -> str:
    return str(uuid.uuid4())
