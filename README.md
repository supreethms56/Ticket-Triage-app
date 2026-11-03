# Ticket Triage

A small Flask app for the Ledgerleaf support team. Customers submit tickets; an AI model
(or keyword rules as a fallback) sorts each ticket by category and priority, writes a
one-line summary, and drafts a reply an agent can edit.

**Status:** Day 1 (Tuesday). Form, database and list page work. AI triage, fallback
rules, filters and the detail page come on Wednesday.

## Setup

Needs Python 3.10 or newer.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # Windows: copy .env.example .env
```

## Run

```bash
python seed.py      # loads the 20 sample tickets (safe to run twice)
python app.py       # http://127.0.0.1:5000
```

## Test

```bash
pytest
```

## LM Studio (for Wednesday)

1. Install LM Studio from lmstudio.ai.
2. Download `LFM2.5-1.2B-Instruct` from LiquidAI (Q4_K_M).
3. Load it and start the server from the Developer tab (default `http://localhost:1234`).
4. Open `http://localhost:1234/v1/models`, copy the model id into `AI_MODEL` in `.env`.

## Project layout

```
app.py          Flask routes (kept thin)
config.py       Categories, priorities, statuses, limits, AI settings
db.py           SQLite schema and queries (parameterized SQL only)
validation.py   New-ticket form checks
seed.py         Loads data/sample_tickets.json without duplicates
templates/      base, list, new, 404
static/         style.css
tests/          pytest tests
```
