"""Load the 20 sample tickets and triage each one. Running it twice adds no duplicates."""
import json
import logging

import config
import db
from triage.service import triage


def seed() -> tuple[int, int]:
    db.init_db()
    with open(config.SAMPLE_TICKETS_PATH, encoding="utf-8") as f:
        tickets = json.load(f)

    added, skipped = 0, 0
    for t in tickets:
        if db.ticket_exists(t["customer_email"], t["subject"], t["created_at"]):
            skipped += 1
            continue
        ticket_id = db.create_ticket(
            customer_name=t["customer_name"],
            customer_email=t["customer_email"],
            subject=t["subject"],
            description=t["description"],
            created_at=t["created_at"],  # keep the original IST time
        )
        result = triage(t["subject"], t["description"], t["customer_name"])
        db.save_triage(ticket_id, result)
        print(f"#{ticket_id:<3} {result['triage_source']:<5} {result['category']:<16} "
              f"{result['priority']:<7} {t['subject']}")
        added += 1
    return added, skipped


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    added, skipped = seed()
    print(f"Added {added} tickets, skipped {skipped} already in the database.")
