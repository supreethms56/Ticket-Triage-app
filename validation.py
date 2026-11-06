"""Checks for the new-ticket form, agent updates and imported tickets."""
import re
from datetime import datetime

import config

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_ticket_form(form) -> tuple[dict, dict]:
    """Return (cleaned values, errors). errors maps field name -> message."""
    values = {
        "customer_name": (form.get("customer_name") or "").strip(),
        "customer_email": (form.get("customer_email") or "").strip(),
        "subject": (form.get("subject") or "").strip(),
        "description": (form.get("description") or "").strip(),
    }
    errors = {}

    if not values["customer_name"]:
        errors["customer_name"] = "Please enter your name."
    elif len(values["customer_name"]) > config.NAME_MAX:
        errors["customer_name"] = f"Name must be {config.NAME_MAX} characters or fewer."

    if not values["customer_email"]:
        errors["customer_email"] = "Please enter your email."
    elif not EMAIL_RE.match(values["customer_email"]):
        errors["customer_email"] = "Please enter a valid email, like name@example.com."

    if not values["subject"]:
        errors["subject"] = "Please enter a subject."
    elif len(values["subject"]) > config.SUBJECT_MAX:
        errors["subject"] = f"Subject must be {config.SUBJECT_MAX} characters or fewer."

    desc_len = len(values["description"])
    if desc_len < config.DESCRIPTION_MIN:
        errors["description"] = (
            f"Please describe the problem in at least {config.DESCRIPTION_MIN} characters "
            f"(you have {desc_len})."
        )
    elif desc_len > config.DESCRIPTION_MAX:
        errors["description"] = (
            f"Description must be {config.DESCRIPTION_MAX} characters or fewer (you have {desc_len})."
        )

    return values, errors


def validate_ticket_update(form) -> tuple[dict, dict]:
    """Check an agent's edit on the detail page."""
    values = {
        "status": (form.get("status") or "").strip(),
        "category": (form.get("category") or "").strip(),
        "priority": (form.get("priority") or "").strip(),
        "suggested_reply": (form.get("suggested_reply") or "").strip(),
    }
    errors = {}
    if values["status"] not in config.STATUSES:
        errors["status"] = "Please choose a status from the list."
    if values["category"] not in config.CATEGORIES:
        errors["category"] = "Please choose a category from the list."
    if values["priority"] not in config.PRIORITIES:
        errors["priority"] = "Please choose a priority from the list."
    if not values["suggested_reply"]:
        errors["suggested_reply"] = "The reply cannot be empty."
    elif len(values["suggested_reply"]) > config.REPLY_MAX_CHARS:
        errors["suggested_reply"] = f"The reply must be {config.REPLY_MAX_CHARS} characters or fewer."
    return values, errors




IMPORT_FIELDS = ("customer_name", "customer_email", "subject", "description")


def validate_import_ticket(item) -> tuple[dict, dict]:
    """Check one ticket from an uploaded JSON file (same format as sample_tickets.json).

    Uses the same rules as the new-ticket form. created_at is optional: if given it must be
    an ISO date-time like '2026-11-02T09:15:00' (IST) and is kept, otherwise the ticket gets
    the current time. Returns (cleaned values, errors)."""
    if not isinstance(item, dict):
        return {}, {"ticket": "Each ticket must be a JSON object with name, email, subject and description."}

    # Only text values count; a number or list in a field is treated as missing.
    form = {f: item[f] for f in IMPORT_FIELDS if isinstance(item.get(f), str)}
    values, errors = validate_ticket_form(form)

    created_at = item.get("created_at")
    if created_at in (None, ""):
        values["created_at"] = None
    else:
        try:
            dt = datetime.fromisoformat(str(created_at).strip())
        except ValueError:
            dt = None
        if dt is None:
            errors["created_at"] = "created_at must be a date and time like 2026-11-02T09:15:00."
        else:
            if dt.tzinfo is not None:  # stored times are IST without an offset
                dt = dt.astimezone(config.IST).replace(tzinfo=None)
            values["created_at"] = dt.isoformat(timespec="seconds")
    return values, errors