"""Re-run triage warns before it replaces an agent's edits.
The real AI is never called: it is replaced with a fake that raises, so the rules triage."""
import sqlite3

import pytest

import config
import db
from app import agent_changes
from triage import ai_client

TICKET = ("Priya Nair", "priya@example.com", "Charged twice",
          "I was charged twice for my subscription this month.")


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


def _new_triaged_ticket(client):
    client.post("/tickets/new", data=dict(zip(
        ("customer_name", "customer_email", "subject", "description"), TICKET)))
    return db.list_tickets()[0]  # Billing / Urgent from the rules


def _agent_saves(client, ticket, **changes):
    form = {"status": ticket["status"], "category": ticket["category"],
            "priority": ticket["priority"], "suggested_reply": ticket["suggested_reply"], **changes}
    client.post(f"/tickets/{ticket['id']}", data=form)
    return db.get_ticket(ticket["id"])


def test_untouched_ticket_retriages_without_asking(client):
    t = _new_triaged_ticket(client)
    r = client.post(f"/tickets/{t['id']}/retriage")
    assert r.status_code == 302  # done straight away
    assert agent_changes(db.get_ticket(t["id"])) == []


def test_saving_without_changes_is_not_an_edit(client):
    t = _new_triaged_ticket(client)
    t = _agent_saves(client, t, status="In progress")  # only the status changed
    assert agent_changes(t) == []


def test_line_endings_alone_are_not_an_edit():
    # Browsers send textarea line breaks as \r\n; that alone is not an edit.
    ticket = {"category": "Billing", "ai_category": "Billing", "priority": "Low",
              "ai_priority": "Low", "ai_reply": "Hi,\nthanks.", "suggested_reply": "Hi,\r\nthanks."}
    assert agent_changes(ticket) == []


def test_edited_ticket_shows_warning_and_keeps_edits(client):
    t = _new_triaged_ticket(client)
    t = _agent_saves(client, t, category="Integrations", priority="Low",
                     suggested_reply="Hi Priya, we are checking this for you.")
    assert len(agent_changes(t)) == 3

    r = client.post(f"/tickets/{t['id']}/retriage")  # no confirm
    page = r.get_data(as_text=True)
    assert r.status_code == 200
    assert "An agent has edited this ticket" in page
    assert "an agent changed it to Integrations" in page
    assert "Replace with new triage" in page

    after = db.get_ticket(t["id"])
    assert (after["category"], after["priority"]) == ("Integrations", "Low")  # nothing replaced
    assert after["suggested_reply"] == "Hi Priya, we are checking this for you."


def test_confirmed_retriage_replaces_edits(client):
    t = _new_triaged_ticket(client)
    t = _agent_saves(client, t, category="Integrations", status="In progress")

    r = client.post(f"/tickets/{t['id']}/retriage", data={"confirm": "yes"})
    assert r.status_code == 302
    after = db.get_ticket(t["id"])
    assert after["category"] == "Billing"
    assert after["status"] == "In progress"  # triage never changes the status
    assert agent_changes(after) == []


def test_old_database_gets_ai_reply_column(tmp_path):
    path = str(tmp_path / "old.db")
    with sqlite3.connect(path) as conn:  # a tickets table from before ai_reply existed
        conn.execute(db.SCHEMA.replace("    ai_reply        TEXT,\n", ""))
        conn.execute("""INSERT INTO tickets (customer_name, customer_email, subject, description,
                        status, suggested_reply, created_at, updated_at)
                        VALUES ('A', 'a@example.com', 'S', 'D', 'Open', 'Hi, thanks.', 'x', 'x')""")
    db.init_db(path)
    t = db.get_ticket(1, db_path=path)
    assert t["ai_reply"] == "Hi, thanks."  # filled from the current reply