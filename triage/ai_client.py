"""The only file that talks to LM Studio. Switching to a cloud model later only changes this file and .env."""
import config
from triage.prompts import SYSTEM_PROMPT

# A JSON schema matching the field table in the brief. LM Studio uses it to
# force the reply shape, but small models may still break it, so service.py
# checks the result either way.
TRIAGE_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "ticket_triage",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "enum": config.CATEGORIES},
                "priority": {"type": "string", "enum": config.PRIORITIES},
                "summary": {"type": "string"},
                "suggested_reply": {"type": "string"},
            },
            "required": ["category", "priority", "summary", "suggested_reply"],
            "additionalProperties": False,
        },
    },
}


class AIError(Exception):
    """Any problem reaching the model or getting text back."""


def get_ai_response(ticket_text: str) -> str:
    """Send one ticket to the model and return its raw text reply. Raises AIError on any failure."""
    if not config.AI_MODEL:
        raise AIError("AI_MODEL is not set in .env")

    try:
        from openai import OpenAI  # imported here so the app still runs in fallback mode without it
    except ImportError as exc:
        raise AIError("The openai package is not installed") from exc

    client = OpenAI(
        base_url=config.AI_BASE_URL,
        api_key="lm-studio",  # LM Studio ignores the key
        timeout=config.AI_TIMEOUT_SECONDS,
        max_retries=0,  # exactly one AI call per ticket, and never more than 30 s
    )
    kwargs = {
        "model": config.AI_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": ticket_text},
        ],
        "temperature": 0,
    }
    if config.AI_USE_JSON_SCHEMA:
        kwargs["response_format"] = TRIAGE_SCHEMA

    try:
        response = client.chat.completions.create(**kwargs)
        raw = response.choices[0].message.content
    except Exception as exc:  # connection refused, timeout, bad request, empty choices...
        raise AIError(f"{type(exc).__name__}: {exc}") from exc

    if not raw:
        raise AIError("The model returned an empty reply")
    return raw
