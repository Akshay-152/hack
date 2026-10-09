"""AI endpoints (spec section 8). All fail gracefully without Ollama.

The discovery assistant grounds answers in real event records retrieved
from the database (RAG) — the model only rephrases, never invents.
"""
from __future__ import annotations

from flask import Blueprint, current_app, g, jsonify, request

from auth_service import auth_required
import db
from helpers import event_to_dict
from services.ollama_client import chat, check_available

bp = Blueprint("ai", __name__)

SYSTEM_ASSISTANT = (
    "You are the Campus Event Bot assistant. Answer ONLY using the event "
    "list provided. If nothing matches, say so. Be brief (under 100 words). "
    "Never invent events.")


def _unavailable():
    return jsonify(error="AI is unavailable right now — the app works "
                         "normally without it."), 503


@bp.get("/api/ai/status")
def ai_status():
    ok, msg = check_available()
    return jsonify({"available": ok, "model": msg if ok else None})


@bp.get("/api/ai/recommendations")
@auth_required()
def ai_recommendations():
    """AI-ranked recommendations with rule-based fallback, never hidden."""
    ok, _ = check_available()
    if not ok:
        return _unavailable()

    profile = db.query_one(
        "SELECT * FROM student_profiles WHERE user_id=?", (g.user["id"],))
    rows = db.query("SELECT * FROM events WHERE status='published' "
                    "ORDER BY event_date LIMIT 30")
    now_date = db.now_iso()[:10]
    events = [event_to_dict(r) for r in rows if r["event_date"] >= now_date]
    if not events:
        return jsonify(recommendations=[], explanation="No published upcoming events.")
    if not profile:
        return jsonify(recommendations=events, explanation="Set up your "
                       "profile to get personalized recommendations.",
                       ruleBased=True)

    listing = "\n".join(
        f"[id={e['id']}] {e['title']} (category: {e['category']}, "
        f"tags: {','.join(e['tags'])}, date: {e['event_date']}, "
        f"venue: {e['venue']})" for e in events)
    prompt = (
        f"Student profile: interests={profile['interests'] or 'none'}, "
        f"preferred categories={profile['preferred_categories'] or 'none'}, "
        f"department={profile['department'] or 'unknown'}, "
        f"semester={profile['semester'] or 'unknown'}.\n"
        f"Upcoming events:\n{listing}\n"
        "Pick the 5 event ids most relevant for this student, sorted "
        "best-first. Reply with ONLY a JSON array of ids, e.g. [3,1,7].")
    text, err = chat([{"role": "user", "content": prompt}])
    if err:
        return _unavailable()

    import json as _json
    import re
    m = re.search(r"\[[\d\s,]*\]", text)
    by_id = {e["id"]: e for e in events}
    ranked = []
    if m:
        try:
            for eid in _json.loads(m.group(0)):
                if eid in by_id and eid not in [e["id"] for e in ranked]:
                    ranked.append(by_id[eid])
        except ValueError:
            pass
    for e in events:  # keep unmatched events visible (spec: don't hide others)
        if e not in ranked:
            ranked.append(e)
    return jsonify(recommendations=ranked, explanation=text[:300])


@bp.post("/api/ai/event-summary")
@auth_required()
def event_summary():
    event_id = (request.get_json(silent=True) or {}).get("eventId")
    row = db.query_one("SELECT * FROM events WHERE id=? AND status='published'",
                       (event_id,))
    if not row:
        return jsonify(error="event not found"), 404
    ok, _ = check_available()
    if not ok:
        return _unavailable()
    text, err = chat([{"role": "user", "content":
                  f"Summarize this campus event in 2-3 short sentences, "
                  f"friendly tone:\n\nTitle: {row['title']}\n"
                  f"Category: {row['category']}\nDescription: "
                  f"{row['description'] or 'n/a'}\nDate: {row['event_date']} "
                  f"{row['start_time']}-{row['end_time']}, venue "
                  f"{row['venue'] or 'n/a'}."}])
    if err:
        return _unavailable()
    return jsonify(summary=text)


@bp.post("/api/ai/assistant")
@auth_required()
def assistant():
    question = ((request.get_json(silent=True) or {}).get("question") or "").strip()
    if not question:
        return jsonify(error="question required"), 400
    ok, _ = check_available()
    if not ok:
        return _unavailable()

    rows = db.query("SELECT * FROM events WHERE status='published' "
                    "ORDER BY event_date LIMIT 40")
    now_date = db.now_iso()[:10]
    events = [event_to_dict(r) for r in rows if r["event_date"] >= now_date]
    listing = "\n".join(
        f"- {e['title']} [{e['category']}], {e['event_date']} "
        f"{e['start_time']}, {e['venue'] or 'venue TBA'}, "
        f"{e['registeredCount']}/{e['capacity']} seats — {e['description'][:150]}"
        for e in events) or "(no upcoming events)"
    text, err = chat([
        {"role": "system", "content": SYSTEM_ASSISTANT},
        {"role": "user", "content": f"Event list:\n{listing}\n\n"
                                    f"Question: {question}"}])
    if err:
        return _unavailable()
    return jsonify(answer=text)


@bp.post("/api/ai/polish-suggestion")
@auth_required()
def polish_suggestion():
    data = request.get_json(silent=True) or {}
    ok, _ = check_available()
    if not ok:
        return _unavailable()
    prompt = (f"Improve this student event suggestion. Keep it factual, "
              f"return JSON with keys title, category, description, reason. "
              f"Category must stay in: coding, ai, sports, music, arts, "
              f"entrepreneurship, volunteering.\nCurrent: "
              f"title={data.get('title')!r}, category={data.get('category')!r}, "
              f"description={data.get('description')!r}, "
              f"reason={data.get('reason')!r}")
    text, err = chat([{"role": "user", "content": prompt}])
    if err:
        return _unavailable()
    import json as _json
    import re
    m = re.search(r"\{.*\}", text, re.S)
    if m:
        try:
            clean = _json.loads(m.group(0))
            if clean.get("category") in ("coding", "ai", "sports", "music",
                                         "arts", "entrepreneurship",
                                         "volunteering"):
                return jsonify(suggestion=clean)
        except ValueError:
            pass
    return jsonify(error="could not produce a valid suggestion"), 502


@bp.post("/api/ai/admin-draft")
@auth_required(require_admin=True)
def admin_draft():
    data = request.get_json(silent=True) or {}
    ok, _ = check_available()
    if not ok:
        return _unavailable()
    prompt = (f"Draft a clear campus event description (3-5 sentences) for:\n"
              f"Title: {data.get('title')!r}\nCategory: {data.get('category')!r}\n"
              f"Venue: {data.get('venue')!r}\nOrganizer: {data.get('organizer')!r}\n"
              f"Extra details: {data.get('details') or 'none'}")
    text, err = chat([{"role": "user", "content": prompt}])
    if err:
        return _unavailable()
    return jsonify(description=text)
