"""Required test 2: parsing and checking the AI reply."""
import json

import pytest

from triage.service import InvalidTriage, parse_ai_reply

VALID = {
    "category": "Billing",
    "priority": "Urgent",
    "summary": "Customer was charged twice for the annual plan.",
    "suggested_reply": "Hi, thank you for letting us know. Our billing team will look into this.",
}


def test_valid_json_passes():
    result = parse_ai_reply(json.dumps(VALID))
    assert result == VALID


def test_json_in_code_fences_passes():
    raw = "```json\n" + json.dumps(VALID, indent=2) + "\n```"
    result = parse_ai_reply(raw)
    assert result["category"] == "Billing"
    assert result["priority"] == "Urgent"


def test_unknown_category_is_rejected():
    bad = {**VALID, "category": "Payments"}
    with pytest.raises(InvalidTriage):
        parse_ai_reply(json.dumps(bad))




def test_integrations_category_is_accepted():
    result = parse_ai_reply(json.dumps({**VALID, "category": "integrations"}))
    assert result["category"] == "Integrations"