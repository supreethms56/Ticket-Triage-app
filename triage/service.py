"""triage(): try the AI, check the result, else use the keyword rules. Never raises."""
import json
import logging
import re
import time

import config
from triage import ai_client, rules
from triage.prompts import build_ticket_text

log = logging.getLogger("triage")

_FENCE_RE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL | re.IGNORECASE)


class InvalidTriage(ValueError):
    """The AI reply is not valid JSON or a field breaks the rules."""


def _canonical(value: str, allowed: list[str]) -> str | None:
    """Match 'billing ' to 'Billing'. Returns None if it is not one of the allowed values."""
    cleaned = value.strip().lower()
    for item in allowed:
        if item.lower() == cleaned:
            return item
    return None


def parse_ai_reply(raw: str) -> dict:
    """Turn the model's raw text into a checked triage dict, or raise InvalidTriage."""
    text = (raw or "").strip()
    match = _FENCE_RE.match(text)
    if match:
        text = match.group(1).strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise InvalidTriage(f"Not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise InvalidTriage("JSON is not an object")

    for field in ("category", "priority", "summary", "suggested_reply"):
        if not isinstance(data.get(field), str) or not data[field].strip():
            raise InvalidTriage(f"Missing or empty field: {field}")

    category = _canonical(data["category"], config.CATEGORIES)
    if category is None:
        raise InvalidTriage(f"Unknown category: {data['category']!r}")
    priority = _canonical(data["priority"], config.PRIORITIES)
    if priority is None:
        raise InvalidTriage(f"Unknown priority: {data['priority']!r}")

    summary = data["summary"].strip()
    if len(summary.split()) > config.SUMMARY_MAX_WORDS:
        raise InvalidTriage(f"Summary is longer than {config.SUMMARY_MAX_WORDS} words")

    reply = data["suggested_reply"].strip()
    if len(reply.split()) > config.REPLY_MAX_WORDS:
        raise InvalidTriage(f"Reply is longer than {config.REPLY_MAX_WORDS} words")
    for pattern in config.FORBIDDEN_REPLY_PATTERNS:
        if re.search(pattern, reply, re.IGNORECASE):
            raise InvalidTriage(f"Reply makes a promise (matched {pattern!r})")

    return {"category": category, "priority": priority,
            "summary": summary, "suggested_reply": reply}


def personalize_reply(reply: str, customer_name: str | None) -> str:
    """Add the first name after the AI call, so the name is never sent to the AI."""
    parts = (customer_name or "").split()
    if not parts:
        return reply
    first = parts[0]
    greeting = re.match(r"^(Hi|Hello|Dear)(\s+there)?\s*[,!]?\s*", reply, re.IGNORECASE)
    if greeting:
        return f"{greeting.group(1)} {first}, {reply[greeting.end():]}"
    return f"Hi {first}, {reply}"


def triage(subject: str, description: str, customer_name: str | None = None) -> dict:
    """Return category, priority, summary, suggested_reply and triage_source ('ai' or 'rules')."""
    start = time.perf_counter()
    try:
        raw = ai_client.get_ai_response(build_ticket_text(subject, description))
        log.debug("Raw AI reply: %s", raw)
        result = parse_ai_reply(raw)
        result["triage_source"] = "ai"
        # Guard: a small model can under-rate a ticket where money is at risk or the
        # customer is locked out. Those clear signals always mean Urgent.
        if result["priority"] != "Urgent" and rules.has_urgent_signal(f"{subject}\n{description}"):
            log.info("Raised AI priority %s to Urgent (money/blocked/data-loss signal)",
                     result["priority"])
            result["priority"] = "Urgent"
    except Exception as exc:  # any AI or checking problem -> keyword rules
        log.warning("AI triage failed, using rules: %s", exc)
        result = rules.triage_with_rules(subject, description)
        result["triage_source"] = "rules"

    result["suggested_reply"] = personalize_reply(result["suggested_reply"], customer_name)
    elapsed = time.perf_counter() - start
    log.info("Triaged with %s in %.2f s: %s / %s", result["triage_source"], elapsed,
             result["category"], result["priority"])
    return result
