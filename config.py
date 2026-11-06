"""All settings in one place. The prompt, the checks, the rules and the dropdowns read from here."""
import os
from datetime import timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# --- Database ---
DATABASE_PATH = os.getenv("DATABASE_PATH", str(BASE_DIR / "tickets.db"))
SAMPLE_TICKETS_PATH = BASE_DIR / "data" / "sample_tickets.json"

# --- Time zone (sample tickets are in IST) ---
# Fixed +05:30 offset: India has no daylight saving, and this works on Windows
# without the extra tzdata package that zoneinfo needs there.
IST = timezone(timedelta(hours=5, minutes=30), "IST")

# --- Ticket values ---
CATEGORIES = ["Billing", "Technical", "Account", "Feature request", "Other"]
PRIORITIES = ["Urgent", "High", "Medium", "Low"]  # highest first, used for sorting
STATUSES = ["Open", "In progress", "Resolved"]
DEFAULT_STATUS = "Open"
TRIAGE_SOURCES = ["ai", "rules"]

# --- Form limits ---
NAME_MAX = 100
SUBJECT_MAX = 120
DESCRIPTION_MIN = 20
DESCRIPTION_MAX = 2000
REPLY_MAX_CHARS = 2000  # agent-edited reply

# --- JSON import on the list page (same format as data/sample_tickets.json) ---
IMPORT_MAX_TICKETS = 200
IMPORT_MAX_FILE_BYTES = 1_000_000  # 1 MB

# --- AI output limits ---
SUMMARY_MAX_WORDS = 15
REPLY_MAX_WORDS = 120

# A reply must never promise a refund, a date or a fix. These patterns are
# checked (ignoring case) before an AI reply is saved.
FORBIDDEN_REPLY_PATTERNS = [
    r"\brefund (has|have) been (approved|processed|issued|initiated)\b",
    r"\b(we will|we'll|we will be able to) (refund|reimburse)\b",
    r"\byou will (be refunded|receive a refund|get a refund)\b",
    r"\brefund will be\b",
    r"\bwe have (refunded|approved)\b",
    r"\b(will be|has been|have been) (fixed|resolved|restored|refunded)\b",
    r"\bwe will (fix|resolve|restore)\b",
    r"\bwe'll (fix|resolve|restore)\b",
    r"\b(by|before) (today|tonight|tomorrow|monday|tuesday|wednesday|thursday|friday|saturday|sunday|end of (the )?(day|week))\b",
    r"\bwithin \d+\s*(minutes?|hours?|days?|weeks?)\b",
]

# Refund promises are checked sentence by sentence. A sentence about a refund or money
# back is rejected if it says the refund is approved/processed (always), or uses
# will/has been/get (unless it only says the team will review or look into it).
REFUND_WORDS = r"\b(refund\w*|reimburs\w*|credited back|credit back|money back|amount back|get (your|the) [^.!?]{0,30}\bback)\b"
REFUND_STRONG_WORDS = (r"\b(approved?|processed|processing|initiated|issued|credited|confirmed|"
                       r"granted|reversed|on its way|reach your)\b")
REFUND_WEAK_WORDS = r"(\bwill\b|'ll\b|\bis being\b|\bhas been\b|\bhave been\b|\bget\b|\breceive\b|\bshortly\b|\bsoon\b)"
REFUND_REVIEW_WORDS = r"\b(review\w*|look into|looking into|check\w*|investigat\w*|assess\w*|team will get back)\b"
# --- Fallback keyword rules (matched on subject + description, ignoring case) ---
# Order matters on a tie: the category listed first wins.
CATEGORY_KEYWORDS = {
    "Billing": ["refund", "charged", "charge", "payment", "subscription", "plan", "price",
                "invoice amount", "billing", "paid"],
    "Account": ["login", "log in", "password", "otp", "locked", "sign in", "two-factor",
                "2fa", "account"],
    "Technical": ["error", "crash", "bug", "slow", "not loading", "export", "failed",
                  "not printing", "500"],
    "Feature request": ["feature", "please add", "would be great", "can you add",
                        "roadmap", "dark mode"],
}

# Priority follows the brief's guide. Words describe IMPACT, not tone: a customer
# writing "urgent" is not evidence of urgency on its own, so it is not in these lists.
#
# Urgent: money is at risk or the customer is fully blocked (double charge, locked out, data lost)
URGENT_KEYWORDS = [
    "charged twice", "two times", "double charge", "charged double", "duplicate charge",
    "wrong amount", "locked", "locked out", "can't log in", "cannot log in",
    "unable to log in", "can't login", "cannot login", "can't sign in", "cannot sign in",
    "deleted", "lost", "data loss",
]
# High: a core feature is broken and there is no workaround
HIGH_KEYWORDS = [
    "error", "failed", "fails", "not working", "cannot", "can't", "not printing",
    "not sending", "crash", "crashes",
]
# Low: questions, feature requests, feedback and anything else
LOW_CATEGORIES = ["Feature request", "Other"]
QUESTION_KEYWORDS = [
    "how do i", "how can i", "how to", "is there a way", "can i", "will my", "do you offer",
    "where can i", "where do i", "can you add", "is it possible", "is it on your roadmap",
]
# A "broken" ticket this short says too little to know if a core feature is down: Medium.
VAGUE_MAX_WORDS = 8
# Medium: everything else (something is wrong but the customer can still work)

# Short fixed reply per category, used when the AI is not available.
# "Hi," is replaced with "Hi <first name>," in code.
FALLBACK_REPLIES = {
    "Billing": (
        "Hi, thank you for contacting Ledgerleaf support. We have received your billing "
        "question and a member of our team will review your account and get back to you."
    ),
    "Technical": (
        "Hi, thank you for reporting this. We're sorry for the trouble. Our team will look "
        "into the problem and reply with an update. Any screenshots or steps to reproduce "
        "it would help us."
    ),
    "Account": (
        "Hi, thank you for reaching out about your account. For your security, a member of "
        "our team will verify the details and get back to you."
    ),
    "Feature request": (
        "Hi, thank you for the suggestion. We've shared it with our product team, who review "
        "every request when planning future work."
    ),
    "Other": (
        "Hi, thank you for contacting Ledgerleaf support. A member of our team will read "
        "your message and get back to you."
    ),
}

# --- AI settings ---
AI_BASE_URL = os.getenv("AI_BASE_URL", "http://localhost:1234/v1")
AI_MODEL = os.getenv("AI_MODEL", "")
AI_TIMEOUT_SECONDS = 30
# Set to "false" in .env if your LM Studio version rejects response_format.
AI_USE_JSON_SCHEMA = os.getenv("AI_USE_JSON_SCHEMA", "true").lower() == "true"

# --- Flask ---
SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me")
