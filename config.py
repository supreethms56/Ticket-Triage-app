"""All settings in one place: lists used by the form, database, prompt and checks."""
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
IST = timezone(timedelta(hours=5, minutes=30), "IST")

# --- Ticket values ---
CATEGORIES = ["Billing", "Technical", "Account", "Feature request", "Other"]
PRIORITIES = ["Urgent", "High", "Medium", "Low"]  # highest first, used for sorting
STATUSES = ["Open", "In progress", "Resolved"]
DEFAULT_STATUS = "Open"

# --- Form limits ---
NAME_MAX = 100
SUBJECT_MAX = 120
DESCRIPTION_MIN = 20
DESCRIPTION_MAX = 2000

# --- AI settings (used from Wednesday) ---
AI_BASE_URL = os.getenv("AI_BASE_URL", "http://localhost:1234/v1")
AI_MODEL = os.getenv("AI_MODEL", "")
AI_TIMEOUT_SECONDS = 30

# --- Flask ---
SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me")
