"""Flask app and routes. Routes stay thin: they call db.py (and triage/ from Wednesday)."""
from datetime import datetime
from zoneinfo import ZoneInfo

from flask import Flask, abort, flash, redirect, render_template, request, url_for

import config
import db
from validation import validate_ticket_form

app = Flask(__name__)
app.config["SECRET_KEY"] = config.SECRET_KEY

db.init_db()


@app.template_filter("age")
def age_filter(created_at: str) -> str:
    """'2026-11-02T09:15:00' -> '5 h ago' (times are IST)."""
    try:
        created = datetime.fromisoformat(created_at)
    except (TypeError, ValueError):
        return ""
    now = datetime.now(config.IST).replace(tzinfo=None)
    seconds = max(0, int((now - created).total_seconds()))
    if seconds < 60:
        return "just now"
    if seconds < 3600:
        return f"{seconds // 60} min ago"
    if seconds < 86400:
        return f"{seconds // 3600} h ago"
    return f"{seconds // 86400} d ago"


@app.route("/")
def ticket_list():
    tickets = db.list_tickets()
    return render_template("list.html", tickets=tickets)


@app.route("/tickets/new", methods=["GET", "POST"])
def new_ticket():
    if request.method == "GET":
        return render_template("new.html", values={}, errors={}, config=config)

    values, errors = validate_ticket_form(request.form)
    if errors:
        return render_template("new.html", values=values, errors=errors, config=config), 400

    ticket_id = db.create_ticket(**values)
    # Wednesday: triage the ticket here via triage.service.triage()
    flash(f"Ticket #{ticket_id} submitted.")
    return redirect(url_for("ticket_list"))


@app.errorhandler(404)
def not_found(_error):
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(debug=True)
