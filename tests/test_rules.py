"""Required test 1: the keyword rules."""
from triage.rules import triage_with_rules


def test_charged_twice_is_billing_and_urgent():
    result = triage_with_rules("Charged twice", "I was charged twice for my subscription")
    assert result["category"] == "Billing"
    assert result["priority"] == "Urgent"
