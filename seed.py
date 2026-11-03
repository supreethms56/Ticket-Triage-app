"""Load the 20 sample tickets. Running it twice adds no duplicates.

Tuesday version: loads and saves tickets only.
Wednesday: call triage.service.triage() on each new ticket.
"""
import json

import config
import db


def seed() -> tuple[int, int]:
    db.init_db()
    with open(config.SAMPLE_TICKETS_PATH, encoding="utf-8") as f:
        tickets = json.load(f)

    added, skipped = 0, 0
    for t in tickets:
        if db.ticket_exists(t["customer_email"], t["subject"], t["created_at"]):
            skipped += 1
            continue
        db.create_ticket(
            customer_name=t["customer_name"],
            customer_email=t["customer_email"],
            subject=t["subject"],
            description=t["description"],
            created_at=t["created_at"],  # keep the original IST time
        )
        added += 1
    return added, skipped


if __name__ == "__main__":
    added, skipped = seed()
    print(f"Added {added} tickets, skipped {skipped} already in the database.")
