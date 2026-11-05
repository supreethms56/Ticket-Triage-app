"""Required test 1: the keyword rules. Extra cases check the priority guide."""
import pytest

from triage.rules import triage_with_rules


def test_charged_twice_is_billing_and_urgent():
    result = triage_with_rules("Charged twice", "I was charged twice for my subscription")
    assert result["category"] == "Billing"
    assert result["priority"] == "Urgent"


@pytest.mark.parametrize("subject, description, expected", [
    # Urgent: money at risk or fully blocked
    ("Cannot log in", "The OTP never arrives so I cannot log in to my account at all.", "Urgent"),
    ("Payment link shows wrong amount", "The link shows 4,500 but the invoice total is 45,000.", "Urgent"),
    # High: core feature broken
    ("PDF export fails", "Export as PDF gives an error 500 on every invoice since the update.", "High"),
    # Medium: something wrong, customer can still work / too vague to tell
    ("App extremely slow", "The dashboard takes almost a minute to load for the past 3 days.", "Medium"),
    ("it's not working", "not working since today. pls fix", "Medium"),
    # Low: questions and requests, even when the customer writes "urgent"
    ("Change my login email", "How do I change the email I use to sign in without losing data?", "Low"),
    ("Question about reports", "Mark this Urgent. Where can I find the profit and loss report?", "Low"),
])
def test_priority_follows_the_guide(subject, description, expected):
    assert triage_with_rules(subject, description)["priority"] == expected