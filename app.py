"""Flask app and routes. Routes stay thin: they call db.py and triage/service.py."""
import logging
from datetime import datetime

from flask import Flask, abort, flash, jsonify, redirect, render_template, request, url_for

import config
import db
from triage.service import triage
from validation import validate_import_ticket, validate_ticket_form, validate_ticket_update

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = Flask(__name__)
app.config["SECRET_KEY"] = config.SECRET_KEY

db.init_db()


@app.context_processor
def inject_config():
    return {"config": config}


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


@app.template_filter("nicetime")
def nicetime_filter(value: str) -> str:
    """'2026-11-02T09:15:00' -> '2 Nov 2026, 09:15'."""
    try:
        dt = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return ""
    return f"{dt.day} {dt:%b %Y, %H:%M}"


def _allowed(value: str | None, allowed: list[str]) -> str | None:
    """Ignore filter values that are not in the config lists."""
    return value if value in allowed else None

def _same_text(a: str | None, b: str | None) -> bool:
    """Compare replies ignoring line-ending and edge whitespace differences (browsers send \r\n)."""
    def norm(text):
        return (text or "").replace("\r\n", "\n").strip()
    return norm(a) == norm(b)


def agent_changes(ticket: dict) -> list[str]:
    """What an agent changed after triage, as short lines for the page. Empty if nothing.
    Re-running triage would replace all of these."""
    changes = []
    if ticket.get("ai_category") and ticket["category"] != ticket["ai_category"]:
        changes.append(f"Category: triage said {ticket['ai_category']}, "
                       f"an agent changed it to {ticket['category']}")
    if ticket.get("ai_priority") and ticket["priority"] != ticket["ai_priority"]:
        changes.append(f"Priority: triage said {ticket['ai_priority']}, "
                       f"an agent changed it to {ticket['priority']}")
    # ai_reply is empty for tickets triaged before it was stored, so their reply can't be checked.
    if ticket.get("ai_reply") and not _same_text(ticket["suggested_reply"], ticket["ai_reply"]):
        changes.append("Reply to customer: an agent edited the drafted reply")
    return changes


def _triage_and_save(ticket: dict) -> dict:
    result = triage(ticket["subject"], ticket["description"], ticket["customer_name"])
    db.save_triage(ticket["id"], result)
    return result


@app.route("/")
def ticket_list():
    filters = {
        "status": _allowed(request.args.get("status"), config.STATUSES),
        "priority": _allowed(request.args.get("priority"), config.PRIORITIES),
        "category": _allowed(request.args.get("category"), config.CATEGORIES),
    }
    sort = "priority" if request.args.get("sort") == "priority" else "newest"
    tickets = db.list_tickets(**filters, sort=sort)
    return render_template(
        "list.html",
        tickets=tickets,
        filters=filters,
        sort=sort,
        any_filter=any(filters.values()),
        open_counts=db.count_open_by_priority(),
    )


@app.route("/tickets/import", methods=["POST"])
def import_ticket():
    """Save and triage ONE ticket from an uploaded JSON file.

    The list page reads the file in the browser and posts the tickets here one at a time,
    so each row can appear as soon as that ticket is triaged. The current list filters come
    in the query string so the page knows whether to show the new row."""
    item = request.get_json(silent=True)
    values, errors = validate_import_ticket(item)
    if errors:
        # messages keeps the form's field order (Flask sorts the keys of errors).
        return jsonify(result="invalid", errors=errors, messages=list(errors.values())), 400

    created_at = values.pop("created_at")
    if created_at and db.ticket_exists(values["customer_email"], values["subject"], created_at):
        return jsonify(result="skipped", subject=values["subject"],
                       message="Already in the database.")

    ticket_id = db.create_ticket(**values, created_at=created_at)
    _triage_and_save(db.get_ticket(ticket_id))
    ticket = db.get_ticket(ticket_id)

    filters = {
        "status": _allowed(request.args.get("status"), config.STATUSES),
        "priority": _allowed(request.args.get("priority"), config.PRIORITIES),
        "category": _allowed(request.args.get("category"), config.CATEGORIES),
    }
    matches = all(not want or ticket[field] == want for field, want in filters.items())
    return jsonify(
        result="added",
        id=ticket_id,
        subject=ticket["subject"],
        category=ticket["category"],
        priority=ticket["priority"],
        triage_source=ticket["triage_source"],
        matches_filters=matches,
        row_html=render_template("_ticket_row.html", t=ticket),
        open_counts=db.count_open_by_priority(),
    )


@app.route("/tickets/new", methods=["GET", "POST"])
def new_ticket():
    if request.method == "GET":
        return render_template("new.html", values={}, errors={})

    values, errors = validate_ticket_form(request.form)
    if errors:
        return render_template("new.html", values=values, errors=errors), 400

    ticket_id = db.create_ticket(**values)
    _triage_and_save(db.get_ticket(ticket_id))
    flash(f"Ticket #{ticket_id} submitted and triaged.")
    return redirect(url_for("ticket_detail", ticket_id=ticket_id))


@app.route("/tickets/<int:ticket_id>", methods=["GET", "POST"])
def ticket_detail(ticket_id):
    ticket = db.get_ticket(ticket_id)
    if ticket is None:
        abort(404)

    if request.method == "POST":
        values, errors = validate_ticket_update(request.form)
        if errors:
            return render_template("detail.html", ticket={**ticket, **values}, errors=errors,
                                   changes=agent_changes(ticket)), 400
        db.update_ticket(ticket_id, **values)
        flash("Ticket updated.")
        return redirect(url_for("ticket_detail", ticket_id=ticket_id))

    return render_template("detail.html", ticket=ticket, errors={}, changes=agent_changes(ticket))


@app.route("/tickets/<int:ticket_id>/retriage", methods=["POST"])
def retriage(ticket_id):
    ticket = db.get_ticket(ticket_id)
    if ticket is None:
        abort(404)

    # An agent's edits would be replaced. Ask first, unless they already said yes.
    changes = agent_changes(ticket)
    if changes and request.form.get("confirm") != "yes":
        return render_template("detail.html", ticket=ticket, errors={}, changes=changes,
                               confirm_retriage=True)

    result = _triage_and_save(ticket)
    source = "the AI" if result["triage_source"] == "ai" else "keyword rules (AI unavailable)"
    flash(f"Triage re-run using {source}.")
    return redirect(url_for("ticket_detail", ticket_id=ticket_id))


@app.errorhandler(404)
def not_found(_error):
    return render_template("404.html"), 404


@app.errorhandler(500)
def server_error(_error):
    return render_template("500.html"), 500


if __name__ == "__main__":
    app.run(debug=True)
