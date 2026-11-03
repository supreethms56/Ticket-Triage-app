"""SQLite connection, schema and queries. Parameterized SQL only."""
import sqlite3
from datetime import datetime

import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS tickets (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_name   TEXT NOT NULL,
    customer_email  TEXT NOT NULL,
    subject         TEXT NOT NULL,
    description     TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'Open',
    category        TEXT,
    priority        TEXT,
    ai_category     TEXT,
    ai_priority     TEXT,
    summary         TEXT,
    suggested_reply TEXT,
    triage_source   TEXT,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);
"""


def now_ist() -> str:
    """Current time in IST as 'YYYY-MM-DDTHH:MM:SS' (same format as the sample data)."""
    return datetime.now(config.IST).replace(tzinfo=None).isoformat(timespec="seconds")


def get_connection(db_path: str | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path or config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str | None = None) -> None:
    with get_connection(db_path) as conn:
        conn.executescript(SCHEMA)


def create_ticket(customer_name, customer_email, subject, description,
                  created_at=None, db_path=None) -> int:
    """Save a new ticket with status Open. Returns the new ticket id."""
    created = created_at or now_ist()
    with get_connection(db_path) as conn:
        cur = conn.execute(
            """INSERT INTO tickets
               (customer_name, customer_email, subject, description,
                status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (customer_name, customer_email, subject, description,
             config.DEFAULT_STATUS, created, created),
        )
        return cur.lastrowid


def get_ticket(ticket_id: int, db_path=None):
    with get_connection(db_path) as conn:
        row = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        return dict(row) if row else None


def list_tickets(db_path=None) -> list[dict]:
    """All tickets, newest first."""
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM tickets ORDER BY created_at DESC, id DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def ticket_exists(customer_email, subject, created_at, db_path=None) -> bool:
    """Used by seed.py so running it twice adds no duplicates."""
    with get_connection(db_path) as conn:
        row = conn.execute(
            """SELECT 1 FROM tickets
               WHERE customer_email = ? AND subject = ? AND created_at = ?""",
            (customer_email, subject, created_at),
        ).fetchone()
        return row is not None


def update_status(ticket_id: int, status: str, db_path=None) -> None:
    with get_connection(db_path) as conn:
        conn.execute(
            "UPDATE tickets SET status = ?, updated_at = ? WHERE id = ?",
            (status, now_ist(), ticket_id),
        )
