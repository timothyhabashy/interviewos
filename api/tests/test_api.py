from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from interviewos.http.app import create_app
from interviewos.public import SECRET_FIELDS


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("INTERVIEWOS_AUTH_BYPASS", "1")
    app = create_app("sqlite+pysqlite:///:memory:")
    with TestClient(app) as test_client:
        yield test_client


def _create(client: TestClient, **kwargs) -> dict:
    body = {
        "interview_type": "Research Program",
        "interview_mode": "Mixed",
        "difficulty": "Intermediate",
        "question_count": 3,
        "timer_seconds": 90,
        "opportunity_description": "Summer research in scientific computing.",
        "applicant_background": "First-year who built a Monte Carlo project.",
    }
    body.update(kwargs)
    response = client.post("/v1/sessions", json=body)
    assert response.status_code == 200, response.text
    return response.json()


def _assert_clean(payload: dict) -> None:
    blob = json.dumps(payload)
    for field in SECRET_FIELDS:
        assert f'"{field}"' not in blob


def test_guest_create_submit_complete_report(client: TestClient):
    created = _create(client)
    session_id = created["id"]
    _assert_clean(created)
    assert created["question"]["question_text"]
    assert created["plan"]["resolved_question_count"] == 3

    events = client.get(f"/v1/sessions/{session_id}/events")
    assert events.status_code == 200
    assert "event: question" in events.text
    _assert_clean({"body": events.text})
    for field in SECRET_FIELDS:
        assert field not in events.text

    answers = [
        (
            None,
            "I built a Monte Carlo simulator in Python because I wanted to see how randomness models real systems.",
        ),
        ("A", "I chose this after thinking through the formula."),
        (
            None,
            "This role matters because I have not had research access at my school and I want to learn from people who do this work.",
        ),
    ]
    current = created["question"]
    for i, (choice, text) in enumerate(answers):
        selected = choice
        if current.get("answer_format") == "multiple_choice_with_explanation":
            selected = current["choices"][0]["label"]
        turn = client.post(
            f"/v1/sessions/{session_id}/turns",
            json={"written_response": text, "selected_choice": selected, "source": "text"},
        )
        assert turn.status_code == 200, turn.text
        _assert_clean(turn.json())
        current = turn.json().get("question") or {}

    done = client.post(f"/v1/sessions/{session_id}/complete")
    assert done.status_code == 200, done.text
    report = done.json()["report"]
    assert "overall_score" in report
    assert report["question_reviews"]

    full = client.get(f"/v1/sessions/{session_id}/report")
    assert full.status_code == 200
    body = full.json()
    # Report may include keys after scoring.
    assert "report" in body
    assert any(
        item.get("correct_label") or item.get("correct_explanation")
        for item in body["transcript"]
        if item["question"]["question_type"] == "technical"
    ) or any(
        review.get("correct_answer_if_applicable")
        for review in body["report"]["question_reviews"]
    )


def test_user_a_cannot_read_user_b(client: TestClient):
    created = client.post(
        "/v1/sessions",
        json={
            "interview_type": "Internship",
            "interview_mode": "Qualitative",
            "difficulty": "Beginner",
            "question_count": 3,
        },
        headers={"Authorization": "Bearer user-a"},
    )
    assert created.status_code == 200
    session_id = created.json()["id"]

    blocked = client.get(
        f"/v1/sessions/{session_id}",
        headers={"Authorization": "Bearer user-b"},
    )
    assert blocked.status_code == 403


def test_guest_cannot_read_foreign_cookie_session(client: TestClient):
    created = _create(client)
    session_id = created["id"]
    other = TestClient(client.app)
    other.cookies.clear()
    denied = other.get(f"/v1/sessions/{session_id}")
    assert denied.status_code in {403, 404}


def test_openapi_snapshot(client: TestClient):
    spec = client.get("/openapi.json")
    assert spec.status_code == 200
    payload = spec.json()
    paths = set(payload["paths"].keys())
    for required in {
        "/v1/sessions",
        "/v1/sessions/{session_id}",
        "/v1/sessions/{session_id}/events",
        "/v1/sessions/{session_id}/turns",
        "/v1/sessions/{session_id}/complete",
        "/v1/sessions/{session_id}/report",
        "/v1/history",
    }:
        assert required in paths
    snapshot_dir = Path(__file__).resolve().parent / "snapshots"
    snapshot_dir.mkdir(exist_ok=True)
    snapshot_path = snapshot_dir / "openapi.paths.json"
    current = sorted(paths)
    if not snapshot_path.exists():
        snapshot_path.write_text(json.dumps(current, indent=2) + "\n")
    expected = json.loads(snapshot_path.read_text())
    assert current == expected
