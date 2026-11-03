"""Required test 4: a saved ticket reads back with the same values,
and a status change updates updated_at."""
import time

import db


def test_ticket_round_trip_and_status_update(tmp_path):
    path = str(tmp_path / "test.db")
    db.init_db(path)

    ticket_id = db.create_ticket(
        "Priya Nair", "priya@example.com", "Charged twice",
        "My card was charged two times for the annual plan.",
        created_at="2026-11-02T09:15:00", db_path=path,
    )
    t = db.get_ticket(ticket_id, db_path=path)
    assert t["customer_name"] == "Priya Nair"
    assert t["customer_email"] == "priya@example.com"
    assert t["subject"] == "Charged twice"
    assert t["status"] == "Open"
    assert t["created_at"] == "2026-11-02T09:15:00"

    before = t["updated_at"]
    time.sleep(1)
    db.update_status(ticket_id, "In progress", db_path=path)
    t2 = db.get_ticket(ticket_id, db_path=path)
    assert t2["status"] == "In progress"
    assert t2["updated_at"] != before
