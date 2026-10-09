# Campus Event Management System

Admins create and manage college events; students register, set preferences,
suggest new events, and get personalized recommendations — with optional local
AI via **Ollama (gemma3:4b)**. Plan and requirements: [PLAN.md](PLAN.md).

- **Backend:** Python Flask + SQLite ([backend/](backend/))
- **Frontend:** HTML/CSS/JS single page ([frontend/](frontend/))
- **AI:** local Ollama chat API, backend-only calls, gracefully optional
  ([backend/services/ollama_client.py](backend/services/ollama_client.py))
- **Auth:** session cookies + werkzeug password hashes
  ([backend/auth_service.py](backend/auth_service.py))

## Quick start

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open **http://localhost:5000** — Flask serves both the API and the frontend.

The SQLite database (`backend/campus_events.db`) is created and migrated
automatically on first launch. Delete the file to reset all data.

## Logins

- **Admin (development only):** username `admin`, password `admin`.
  Override via `ADMIN_USERNAME` / `ADMIN_PASSWORD` env vars before first run.
  Hashed at rest; replace with proper provisioning in production.
- **Students:** sign up from the landing page with any valid email and a
  password of 6+ characters.

## Ollama integration

1. Start Ollama: `ollama serve` (usually runs automatically).
2. Verify the model is present: `ollama list` — requires `gemma3:4b`.
   If missing: `ollama pull gemma3:4b`.
3. Confirm from the app: `GET /api/ai/status` → `{"available": true, ...}`.

Configuration (all optional, [see .env.example](.env.example)):

```
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=gemma3:4b
OLLAMA_TIMEOUT=90
```

**AI features** (each degrades gracefully — the app works fully without
Ollama): event summaries, discovery assistant (answers grounded in real
database records), suggestion polishing, admin description drafting,
AI event re-ranking. The rule-based recommender always remains available.

The backend never sends passwords or auth data to the model, and the AI
can never create, publish, edit, or delete events without an authorized
user action.

## Key API groups

`/api/auth/*` (register/login/logout) · `/api/profile` · `/api/events` ·
`/api/events/:id/register` · `/api/my-registrations` ·
`/api/event-suggestions` · `/api/admin/events` (admin) ·
`/api/admin/suggestions` (admin) · `/api/ai/*` (optional) · `/api/health`

Admin endpoints are protected server-side: student sessions get 403.

## Registration logic

- **Internal:** stored in SQLite; duplicates rejected (409); capacity and
  deadline enforced server-side.
- **External (Google Forms etc.):** tracked as `pending_external` — the app
  does not claim completion it cannot verify.
- **Both:** the Register button does internal registration; an additional
  button opens the external form.

## Tests

```bash
python -m pytest tests -q
```

32 tests covering the acceptance scenarios: admin login, student
register/re-login, profile persistence, admin CRUD + publish lifecycle,
duplicate/capacity/deadline registration rules, suggestion flow, role
restrictions, recommendations by preference, and app functionality with
Ollama stopped.

## Project structure

```
backend/   app.py, db.py (SQLite), auth_service.py, helpers.py, config.py
           routes/  auth_routes, events, registrations, profile,
                    recommendations, suggestions, admin, ai
           services/  ollama_client.py, recommender.py
           uploads/   posters and profile photos (created at runtime)
frontend/  index.html, css/style.css, js/app.js
tests/     pytest suite
```
