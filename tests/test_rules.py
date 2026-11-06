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


    

@pytest.mark.parametrize("subject, description, expected_priority", [
    # Technical words ("error", "failed") must not pull a bank sync ticket into Technical
    ("Bank sync failed", "Bank sync failed with an error and no transactions came in since Monday.", "High"),
    # "bank account" contains the Account word "account", but this is about bank sync
    ("Linking my bank", "How do I connect my bank account to Ledgerleaf for bank feeds?", "Low"),
        ("Missing entries", "Bank transactions from last week are missing in the reconciliation screen.", "Medium"),
    # A payment was made but still shows unpaid: Integrations, not Billing
    ("Payment status", "I Paid the Money but the payment is still showing unpaid", "Medium"),
])
def test_bank_sync_is_integrations(subject, description, expected_priority):
    result = triage_with_rules(subject, description)
    assert result["category"] == "Integrations"
    assert result["priority"] == expected_priority
    assert "bank" in result["suggested_reply"]


def test_bank_word_alone_does_not_mean_integrations():
    result = triage_with_rules("Refund to my bank", "Please refund the extra charge to my bank.")
    assert result["category"] == "Billing"