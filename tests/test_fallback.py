"""Required test 3: when the AI client raises an error, triage uses the rules.
The real AI is never called: monkeypatch replaces it with a fake that raises."""
from triage import ai_client, service


def test_ai_error_falls_back_to_rules(monkeypatch):
    def fake_ai(_ticket_text):
        raise ai_client.AIError("LM Studio is not running")

    monkeypatch.setattr(ai_client, "get_ai_response", fake_ai)

    result = service.triage("Charged twice", "I was charged twice for my subscription")
    assert result["triage_source"] == "rules"
    assert result["category"] == "Billing"
    assert result["priority"] == "Urgent"
    assert result["suggested_reply"]
