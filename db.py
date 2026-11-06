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
    ai_reply        TEXT,
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
        # Databases made before ai_reply existed: add the column and fill it with each
        # ticket's current reply, so reply edits from now on can be noticed.
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(tickets)")}
        if "ai_reply" not in columns:
            conn.execute("ALTER TABLE tickets ADD COLUMN ai_reply TEXT")
            conn.execute("UPDATE tickets SET ai_reply = suggested_reply")


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


def save_triage(ticket_id: int, result: dict, db_path=None) -> None:
    """Store a triage result. Sets both the current values and the originals (ai_ columns),
    so an agent's later edits can be told apart from what triage suggested."""
    with get_connection(db_path) as conn:
        conn.execute(
            """UPDATE tickets
               SET category = ?, priority = ?, ai_category = ?, ai_priority = ?,
                   summary = ?, suggested_reply = ?, ai_reply = ?, triage_source = ?,
                   updated_at = ?
               WHERE id = ?""",
            (result["category"], result["priority"], result["category"], result["priority"],
             result["summary"], result["suggested_reply"], result["suggested_reply"],
             result["triage_source"], now_ist(), ticket_id),
        )


def get_ticket(ticket_id: int, db_path=None):
    with get_connection(db_path) as conn:
        row = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        return dict(row) if row else None


def list_tickets(status=None, priority=None, category=None, sort=None, db_path=None) -> list[dict]:
    """Tickets, newest first, or highest priority first when sort == 'priority'.
    Filter values must already be checked against config lists by the caller."""
    # Fixed SQL: an empty filter (NULL) matches every row.
    sql = """SELECT * FROM tickets
             WHERE (? IS NULL OR status = ?)
               AND (? IS NULL OR priority = ?)
               AND (? IS NULL OR category = ?)
             ORDER BY created_at DESC, id DESC"""
    status, priority, category = status or None, priority or None, category or None
    params = (status, status, priority, priority, category, category)

    with get_connection(db_path) as conn:
        tickets = [dict(r) for r in conn.execute(sql, params).fetchall()]

    if sort == "priority":
        # Stable sort keeps newest-first inside each priority. Untriaged tickets go last.
        rank = {name: i for i, name in enumerate(config.PRIORITIES)}
        tickets.sort(key=lambda t: rank.get(t["priority"], len(rank)))
    return tickets


def count_open_by_priority(db_path=None) -> dict:
    """{'Urgent': 3, 'High': 1, ...} for open tickets."""
    counts = {p: 0 for p in config.PRIORITIES}
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT priority, COUNT(*) AS n FROM tickets WHERE status = ? GROUP BY priority",
            (config.DEFAULT_STATUS,),
        ).fetchall()
    for r in rows:
        if r["priority"] in counts:
            counts[r["priority"]] = r["n"]
    return counts


def ticket_exists(customer_email, subject, created_at, db_path=None) -> bool:
    """Used by seed.py so running it twice adds no duplicates."""
    with get_connection(db_path) as conn:
        row = conn.execute(
            """SELECT 1 FROM tickets
               WHERE customer_email = ? AND subject = ? AND created_at = ?""",
            (customer_email, subject, created_at),
        ).fetchone()
        return row is not None


def update_ticket(ticket_id: int, status: str, category: str, priority: str,
                  suggested_reply: str, db_path=None) -> None:
    """An agent's edit. Never touches ai_category or ai_priority."""
    with get_connection(db_path) as conn:
        conn.execute(
            """UPDATE tickets
               SET status = ?, category = ?, priority = ?, suggested_reply = ?, updated_at = ?
               WHERE id = ?""",
            (status, category, priority, suggested_reply, now_ist(), ticket_id),
        )


def update_status(ticket_id: int, status: str, db_path=None) -> None:
    with get_connection(db_path) as conn:
        conn.execute(
            "UPDATE tickets SET status = ?, updated_at = ? WHERE id = ?",
            (status, now_ist(), ticket_id),
        )
