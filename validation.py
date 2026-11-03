"""Checks for the new-ticket form."""
import re

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
