"""Uploading tickets from a JSON file on the list page (POST /tickets/import, one ticket per call).
The real AI is never called: it is replaced with a fake that raises, so the rules triage."""
import pytest

import config
import db
from triage import ai_client
from validation import validate_import_ticket

GOOD = {
    "customer_name": "Priya Nair",
    "customer_email": "priya@example.com",
    "subject": "Charged twice for annual plan",
    "description": "My card was charged two times for the annual plan yesterday.",
    "created_at": "2026-11-02T09:15:00",
}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATABASE_PATH", str(tmp_path / "test.db"))
    db.init_db()

    def no_ai(_text):
        raise ai_client.AIError("LM Studio is not running")

    monkeypatch.setattr(ai_client, "get_ai_response", no_ai)
    from app import app
    app.config["TESTING"] = True
    return app.test_client()


def test_valid_ticket_keeps_its_created_at():
    values, errors = validate_import_ticket(GOOD)
    assert errors == {}
    assert values["created_at"] == "2026-11-02T09:15:00"


def test_created_at_is_optional():
    values, errors = validate_import_ticket({k: v for k, v in GOOD.items() if k != "created_at"})
    assert errors == {}
    assert values["created_at"] is None


def test_bad_tickets_are_rejected():
    _, errors = validate_import_ticket({**GOOD, "customer_email": "not-an-email", "created_at": "yesterday"})
    assert set(errors) == {"customer_email", "created_at"}
    _, errors = validate_import_ticket({**GOOD, "subject": 42})  # a number is not a subject
    assert "subject" in errors
    _, errors = validate_import_ticket(["not", "an", "object"])
    assert errors


def test_import_adds_triages_and_returns_a_row(client):
    r = client.post("/tickets/import", json=GOOD)
    data = r.get_json()
    assert r.status_code == 200
    assert data["result"] == "added"
    assert data["triage_source"] == "rules"
    assert (data["category"], data["priority"]) == ("Billing", "Urgent")
    assert f'data-id="{data["id"]}"' in data["row_html"]
    assert data["open_counts"]["Urgent"] == 1

    saved = db.get_ticket(data["id"])
    assert saved["created_at"] == "2026-11-02T09:15:00"
    assert saved["suggested_reply"].startswith("Hi Priya,")


def test_same_ticket_twice_is_skipped(client):
    client.post("/tickets/import", json=GOOD)
    r = client.post("/tickets/import", json=GOOD)
    assert r.get_json()["result"] == "skipped"
    assert len(db.list_tickets()) == 1


def test_invalid_ticket_returns_errors_and_saves_nothing(client):
    r = client.post("/tickets/import", json={**GOOD, "description": "too short"})
    assert r.status_code == 400
    assert r.get_json()["result"] == "invalid"
    assert "description" in r.get_json()["errors"]
    assert db.list_tickets() == []


def test_matches_filters_follows_the_list_filters(client):
    r = client.post("/tickets/import?priority=Low", json=GOOD)
    assert r.get_json()["matches_filters"] is False  # saved, but not shown in a Low-only view
    r = client.post("/tickets/import?priority=Urgent&status=Open",
                    json={**GOOD, "created_at": "2026-11-03T10:00:00"})
    assert r.get_json()["matches_filters"] is True