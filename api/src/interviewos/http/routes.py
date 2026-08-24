from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session as DbSession
from starlette.responses import StreamingResponse

from interviewos.constants import (
    DIFFICULTY_LEVELS,
    INTERVIEW_MODES,
    INTERVIEW_TYPES,
    SAMPLES,
)
from interviewos.engine import InterviewEngine
from interviewos.http.auth import Principal, assert_can_access, get_principal
from interviewos.http.db import ReportRow, SessionRow
from interviewos.http.schemas import (
    CompleteResponse,
    CreateSessionRequest,
    HistoryItem,
    MetaResponse,
    SessionCreated,
    SessionView,
    SubmitTurnRequest,
    SubmitTurnResponse,
)
from interviewos.http.settings import live_mode
from interviewos.http.store import (
    ensure_user,
    load_engine,
    new_session_id,
    persist_engine,
    record_turn,
)
from interviewos.models import Answer, InterviewConfig
from interviewos.public import assert_no_secrets

router = APIRouter()


def get_db(request: Request) -> DbSession:
    factory = request.app.state.session_factory
    db = factory()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _session_or_404(db: DbSession, session_id: str) -> SessionRow:
    row = db.get(SessionRow, session_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return row


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/v1/meta", response_model=MetaResponse)
def meta() -> MetaResponse:
    return MetaResponse(
        interview_types=list(INTERVIEW_TYPES),
        interview_modes=list(INTERVIEW_MODES),
        difficulty_levels=list(DIFFICULTY_LEVELS),
        samples=SAMPLES,
        live=live_mode(),
    )


@router.post("/v1/sessions", response_model=SessionCreated)
def create_session(
    body: CreateSessionRequest,
    principal: Principal = Depends(get_principal),
    db: DbSession = Depends(get_db),
) -> SessionCreated:
    config = InterviewConfig(**body.model_dump())
    engine = InterviewEngine(config, live=live_mode())
    question = engine.start()
    payload = question.model_dump()
    assert_no_secrets(payload)
    session_id = new_session_id()
    owner_id = None
    if principal.user_id:
        ensure_user(db, principal.user_id)
        owner_id = principal.user_id
    row = SessionRow(
        id=session_id,
        owner_id=owner_id,
        guest_id=None if owner_id else principal.guest_id,
        status=engine.status,
        engine_state={},
    )
    persist_engine(db, row, engine)
    db.add(row)
    db.flush()
    return SessionCreated(
        id=session_id,
        status=engine.status,
        plan=engine.plan,
        question=question,
        live=live_mode(),
    )


@router.get("/v1/sessions/{session_id}", response_model=SessionView)
def get_session(
    session_id: str,
    principal: Principal = Depends(get_principal),
    db: DbSession = Depends(get_db),
) -> SessionView:
    row = _session_or_404(db, session_id)
    assert_can_access(row.owner_id, row.guest_id, principal)
    engine = load_engine(row, live=live_mode())
    question = engine.current_public_question()
    if question:
        assert_no_secrets(question.model_dump())
    return SessionView(
        id=row.id,
        status=engine.status,
        plan=engine.plan,
        config=engine.config,
        question=question,
        answered_count=len(engine.turns),
        owner_id=row.owner_id,
    )


@router.get("/v1/sessions/{session_id}/events")
async def session_events(
    session_id: str,
    request: Request,
    principal: Principal = Depends(get_principal),
    db: DbSession = Depends(get_db),
):
    row = _session_or_404(db, session_id)
    assert_can_access(row.owner_id, row.guest_id, principal)
    engine = load_engine(row, live=live_mode())
    question = engine.current_public_question()
    if question is None:
        raise HTTPException(status_code=409, detail="No pending question")
    assert_no_secrets(question.model_dump())
    text = question.question_text

    async def gen():
        for i in range(0, len(text), 24):
            if await request.is_disconnected():
                break
            chunk = text[i : i + 24]
            yield f"event: token\ndata: {json.dumps({'text': chunk})}\n\n"
        yield f"event: question\ndata: {json.dumps(question.model_dump())}\n\n"
        yield (
            "event: timer_start\ndata: "
            + json.dumps({"timer_seconds": engine.plan.resolved_timer_seconds})
            + "\n\n"
        )

    return StreamingResponse(gen(), media_type="text/event-stream")


@router.post("/v1/sessions/{session_id}/turns", response_model=SubmitTurnResponse)
def submit_turn(
    session_id: str,
    body: SubmitTurnRequest,
    principal: Principal = Depends(get_principal),
    db: DbSession = Depends(get_db),
) -> SubmitTurnResponse:
    row = _session_or_404(db, session_id)
    assert_can_access(row.owner_id, row.guest_id, principal)
    engine = load_engine(row, live=live_mode())
    if engine.status not in {"in_progress", "ready"}:
        raise HTTPException(status_code=409, detail="Session is not accepting answers")
    written = (body.written_response or "").strip()
    if not written:
        raise HTTPException(status_code=422, detail="written_response is required")
    pending = engine.pending_question
    if pending and pending.answer_format == "multiple_choice_with_explanation" and not body.selected_choice:
        raise HTTPException(status_code=422, detail="selected_choice is required")
    nxt = engine.submit(
        Answer(
            written_response=written,
            selected_choice=body.selected_choice,
            time_expired=body.time_expired,
            source=body.source,
        )
    )
    record_turn(db, row.id, engine)
    persist_engine(db, row, engine)
    if nxt:
        assert_no_secrets(nxt.model_dump())
    return SubmitTurnResponse(
        id=row.id,
        status=engine.status,
        question=nxt,
        answered_count=len(engine.turns),
    )


@router.post("/v1/sessions/{session_id}/complete", response_model=CompleteResponse)
def complete_session(
    session_id: str,
    principal: Principal = Depends(get_principal),
    db: DbSession = Depends(get_db),
) -> CompleteResponse:
    row = _session_or_404(db, session_id)
    assert_can_access(row.owner_id, row.guest_id, principal)
    engine = load_engine(row, live=live_mode())
    if engine.status == "complete":
        existing = db.get(ReportRow, row.id)
        if existing:
            from interviewos.models import Feedback

            return CompleteResponse(
                id=row.id, status="complete", report=Feedback.model_validate(existing.payload)
            )
    if engine.status not in {"awaiting_score", "complete"} and len(engine.turns) < engine.plan.resolved_question_count:
        raise HTTPException(status_code=409, detail="Interview is not finished")
    report = engine.complete()
    persist_engine(db, row, engine)
    db.merge(ReportRow(session_id=row.id, payload=report.model_dump(mode="json")))
    return CompleteResponse(id=row.id, status=engine.status, report=report)


@router.get("/v1/sessions/{session_id}/report")
def get_report(
    session_id: str,
    principal: Principal = Depends(get_principal),
    db: DbSession = Depends(get_db),
):
    row = _session_or_404(db, session_id)
    assert_can_access(row.owner_id, row.guest_id, principal)
    report = db.get(ReportRow, row.id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    engine = load_engine(row, live=False)
    # Secrets are allowed on the report, never on the question stream.
    return {
        "id": row.id,
        "status": row.status,
        "plan": engine.plan.model_dump(),
        "config": engine.config.model_dump(),
        "report": report.payload,
        "transcript": [
            {
                "question": t.question.model_dump(
                    exclude={"correct_label", "correct_explanation"}
                ),
                "answer": t.answer.model_dump(),
                "correct_label": t.question.correct_label,
                "correct_explanation": t.question.correct_explanation,
            }
            for t in engine.turns
        ],
    }


@router.post("/v1/sessions/{session_id}/claim")
def claim_session(
    session_id: str,
    principal: Principal = Depends(get_principal),
    db: DbSession = Depends(get_db),
):
    if not principal.user_id:
        raise HTTPException(status_code=401, detail="Sign in to save this report")
    row = _session_or_404(db, session_id)
    assert_can_access(row.owner_id, row.guest_id, principal)
    ensure_user(db, principal.user_id)
    row.owner_id = principal.user_id
    db.add(row)
    return {"id": row.id, "owner_id": row.owner_id}


@router.post("/v1/sessions/{session_id}/retry", response_model=SessionCreated)
def retry_session(
    session_id: str,
    principal: Principal = Depends(get_principal),
    db: DbSession = Depends(get_db),
) -> SessionCreated:
    from interviewos.constants import DIFFICULTY_LADDER

    row = _session_or_404(db, session_id)
    assert_can_access(row.owner_id, row.guest_id, principal)
    engine = load_engine(row, live=live_mode())
    current = engine.plan.resolved_difficulty
    try:
        idx = DIFFICULTY_LADDER.index(current)
        nxt = DIFFICULTY_LADDER[min(idx + 1, len(DIFFICULTY_LADDER) - 1)]
    except ValueError:
        nxt = current
    body = CreateSessionRequest(
        interview_type=engine.config.interview_type,
        interview_mode=engine.config.interview_mode,
        difficulty=nxt,
        question_count=engine.config.question_count,
        timer_seconds=engine.config.timer_seconds,
        opportunity_description=engine.config.opportunity_description,
        applicant_background=engine.config.applicant_background,
    )
    return create_session(body, principal, db)


@router.get("/v1/history", response_model=list[HistoryItem])
def history(
    principal: Principal = Depends(get_principal),
    db: DbSession = Depends(get_db),
) -> list[HistoryItem]:
    if not principal.user_id:
        raise HTTPException(status_code=401, detail="Sign in to view history")
    rows = (
        db.query(SessionRow)
        .filter(SessionRow.owner_id == principal.user_id)
        .order_by(SessionRow.created_at.desc())
        .all()
    )
    items: list[HistoryItem] = []
    for row in rows:
        engine = load_engine(row, live=False)
        report = db.get(ReportRow, row.id)
        items.append(
            HistoryItem(
                id=row.id,
                status=row.status,
                interview_type=engine.config.interview_type,
                difficulty=engine.plan.resolved_difficulty,
                mode=engine.plan.resolved_mode,
                overall_score=(report.payload.get("overall_score") if report else None),
                created_at=row.created_at.isoformat() if row.created_at else "",
            )
        )
    return items


@router.get("/v1/history/compare")
def compare(
    left: str,
    right: str,
    principal: Principal = Depends(get_principal),
    db: DbSession = Depends(get_db),
):
    def load(sid: str):
        row = _session_or_404(db, sid)
        assert_can_access(row.owner_id, row.guest_id, principal)
        report = db.get(ReportRow, sid)
        if report is None:
            raise HTTPException(status_code=404, detail="Report not found")
        engine = load_engine(row, live=False)
        return {
            "id": sid,
            "plan": engine.plan.model_dump(),
            "report": report.payload,
        }

    return {"left": load(left), "right": load(right)}
