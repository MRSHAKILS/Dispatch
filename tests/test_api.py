"""API-level tests using FastAPI's TestClient."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "version" in body and "time" in body


def test_sort_ticket_happy_path():
    r = client.post(
        "/sort-ticket",
        json={
            "ticket_id": "T-001",
            "channel": "app",
            "locale": "en",
            "message": "I sent 5000 taka to a wrong number this morning",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["ticket_id"] == "T-001"
    assert body["case_type"] == "wrong_transfer"
    assert set(body) == {
        "ticket_id",
        "case_type",
        "severity",
        "department",
        "agent_summary",
        "human_review_required",
        "confidence",
    }


def test_sort_ticket_minimal_body():
    # channel and locale are optional.
    r = client.post("/sort-ticket", json={"ticket_id": "T-9", "message": "app crashed"})
    assert r.status_code == 200
    assert r.json()["case_type"] == "other"


def test_missing_message_is_rejected():
    r = client.post("/sort-ticket", json={"ticket_id": "T-1"})
    assert r.status_code == 422


def test_dashboard_served_at_root():
    r = client.get("/")
    assert r.status_code == 200
    assert "Dispatch" in r.text
