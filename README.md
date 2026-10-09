# Campus Event Recommendation Bot

Web app that recommends college events to students based on their interests,
academic year, and department. Built per [PLAN.md](PLAN.md).

- **Backend:** Python Flask (see [backend/](backend/))
- **Frontend:** HTML/CSS/JS single page (see [frontend/](frontend/))
- **Storage:** in-memory store for local dev, Firebase Firestore for production
  ([backend/storage.py](backend/storage.py), [firestore.rules](firestore.rules))
- **Recommendation engine:** transparent rule-based scorer
  ([backend/services/recommender.py](backend/services/recommender.py))

## Quick start (dev mode — no Firebase needed)

```bash
cd backend
python -m venv venv
venv/Scripts/activate          # Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open http://localhost:5000 — the Flask server also serves the frontend.

Sign in with any ID (e.g. `s123`). Tick **"Sign in as admin (demo)"** to
access the admin dashboard.

## Firestore mode

1. Create a Firebase project → enable Authentication + Firestore.
2. Get a service-account key and save it locally (never commit it).
3. Copy [.env.example](.env.example) to `.env` and set:

   ```
   DB_BACKEND=firestore
   FIREBASE_CREDENTIALS=path/to/serviceAccountKey.json
   FIREBASE_PROJECT_ID=your-project-id
   ```

4. Deploy rules: `firebase deploy --only firestore:rules`

## Tests

```bash
cd backend            # or from repo root using tests/conftest path setup
pytest ../tests -v
```

Covers recommendation scoring rules (PLAN §6.3), registration constraints
(duplicates / capacity / deadline), admin authorization, and API filters.

## API overview

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET  | `/api/health` | Liveness check |
| POST | `/api/auth/demo-login` | Dev sign-in, returns bearer token |
| GET  | `/api/me` | Current user (token required) |
| GET/PUT | `/api/profile` | View / update profile |
| PUT  | `/api/profile/interests` | Update interests |
| GET  | `/api/events` | Published upcoming events (filters: `category`, `date`, `department`, `q`) |
| GET  | `/api/events/<id>` | Event details |
| GET  | `/api/recommendations` | Personalized ranked events |
| POST | `/api/events/<id>/register` | Register (dedupe, capacity, deadline enforced) |
| POST | `/api/events/<id>/cancel-registration` | Cancel registration |
| GET  | `/api/my-registrations` | My registrations |
| POST/GET | `/api/admin/events` | Admin: create / list all events |
| PUT  | `/api/admin/events/<id>` | Admin: update event |
| POST | `/api/admin/events/<id>/cancel` | Admin: cancel event |

## Scoring rules

From [PLAN.md](PLAN.md) §6.3 (weights tunable in `.env`/`config.py`):

- Category match: **+3** · each matched tag **+2**
- Department/year in targetAudience: **+1** · registration open **+1**
- Past, cancelled, and draft events are excluded
- Sorted by match score DESC, then date ASC

## Project structure

```
backend/    Flask app, routes, services, config
frontend/   index.html, css/, js/
tests/      pytest: recommender + API integration
firestore.rules
.env.example
PLAN.md / TODO.md
```
