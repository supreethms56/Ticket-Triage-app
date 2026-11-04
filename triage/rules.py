"""Keyword fallback triage. Used when the AI is unavailable or its reply fails the checks."""
import re

import config


def _contains(text: str, keyword: str) -> bool:
    """Whole-word match, ignoring case ('plan' matches 'plan' but not 'explain')."""
    pattern = r"(?<!\w)" + re.escape(keyword.lower()) + r"(?!\w)"
    return re.search(pattern, text) is not None


def pick_category(text: str) -> str:
    text = text.lower()
    best, best_hits = "Other", 0
    for category, keywords in config.CATEGORY_KEYWORDS.items():
        hits = sum(1 for kw in keywords if _contains(text, kw))
        if hits > best_hits:  # strict '>' so the earlier category wins a tie
            best, best_hits = category, hits
    return best


def pick_priority(text: str, category: str) -> str:
    text = text.lower()
    if any(_contains(text, kw) for kw in config.URGENT_KEYWORDS):
        return "Urgent"
    if any(_contains(text, kw) for kw in config.HIGH_KEYWORDS):
        return "High"
    if category in config.LOW_CATEGORIES:
        return "Low"
    return "Medium"


def make_summary(subject: str) -> str:
    """No AI, so the summary is the subject, cut to the word limit."""
    words = subject.split()
    summary = " ".join(words[: config.SUMMARY_MAX_WORDS])
    return summary if len(words) <= config.SUMMARY_MAX_WORDS else summary + "…"


def triage_with_rules(subject: str, description: str) -> dict:
    text = f"{subject}\n{description}"
    category = pick_category(text)
    return {
        "category": category,
        "priority": pick_priority(text, category),
        "summary": make_summary(subject),
        "suggested_reply": config.FALLBACK_REPLIES[category],
    }
