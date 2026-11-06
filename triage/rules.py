"""Keyword fallback triage. Used when the AI is unavailable or its reply fails the checks."""
import re

import config


def _contains(text: str, keyword: str) -> bool:
    """Whole-word match, ignoring case ('plan' matches 'plan' but not 'explain')."""
    pattern = r"(?<!\w)" + re.escape(keyword.lower()) + r"(?!\w)"
    return re.search(pattern, text) is not None


def decisive_category(text: str) -> str | None:
    """The category of the first decisive phrase found (like "bank sync"), else None.
    Also used to guard the AI's category."""
    text = text.lower()
    for category, keywords in config.DECISIVE_CATEGORY_KEYWORDS.items():
        if any(_contains(text, kw) for kw in keywords):
            return category
    return None


def pick_category(text: str) -> str:
    # A decisive phrase wins outright, whatever else the ticket says.
    decisive = decisive_category(text)
    if decisive:
        return decisive
    text = text.lower()
    best, best_hits = "Other", 0
    for category, keywords in config.CATEGORY_KEYWORDS.items():
        hits = sum(1 for kw in keywords if _contains(text, kw))
        if hits > best_hits:  # strict '>' so the earlier category wins a tie
            best, best_hits = category, hits
    return best


def has_urgent_signal(text: str) -> bool:
    """Money at risk, locked out or data lost. Also used to guard the AI's priority."""
    text = text.lower()
    return any(_contains(text, kw) for kw in config.URGENT_KEYWORDS)


def pick_priority(text: str, category: str, description: str = "") -> str:
    """Apply the priority guide, from most to least serious."""
    lowered = text.lower()
    if has_urgent_signal(lowered):
        return "Urgent"
    if any(_contains(lowered, kw) for kw in config.HIGH_KEYWORDS):
        too_vague = len(description.split()) <= config.VAGUE_MAX_WORDS
        return "Medium" if too_vague else "High"
    if category in config.LOW_CATEGORIES:
        return "Low"
    if any(_contains(lowered, kw) for kw in config.QUESTION_KEYWORDS):
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
        "priority": pick_priority(text, category, description),
        "summary": make_summary(subject),
        "suggested_reply": config.FALLBACK_REPLIES.get(category, config.FALLBACK_REPLIES["Other"]),
    }