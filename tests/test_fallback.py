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




def test_ai_priority_raised_when_money_is_at_risk(monkeypatch):
    """The AI said Medium for a double charge; the guard raises it to Urgent."""
    import json
    reply = {"category": "Billing", "priority": "Medium",
             "summary": "Customer was charged twice for the annual plan.",
             "suggested_reply": "Hi, thank you for letting us know. Our billing team will look into it."}
    monkeypatch.setattr(ai_client, "get_ai_response", lambda _text: json.dumps(reply))

    result = service.triage("Charged twice", "My card was charged two times for the annual plan.")
    assert result["triage_source"] == "ai"
    assert result["priority"] == "Urgent"


    

def test_ai_category_changed_when_ticket_is_about_bank_sync(monkeypatch):
    """The AI said Billing for a paid-but-unpaid ticket; the guard changes it to Integrations."""
    import json
    reply = {"category": "Billing", "priority": "Medium",
             "summary": "Customer paid but the payment still shows unpaid.",
             "suggested_reply": "Hi, thank you for letting us know. Our team will look into it."}
    monkeypatch.setattr(ai_client, "get_ai_response", lambda _text: json.dumps(reply))

    result = service.triage("Payment status", "I Paid the Money but the payment is still showing unpaid")
    assert result["triage_source"] == "ai"
    assert result["category"] == "Integrations"