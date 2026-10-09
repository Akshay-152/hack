# Campus Event Recommendation Bot — Requirements Analysis & TODO

Derived from [PLAN.md](PLAN.md). Stack: **Python (Flask) backend + HTML/CSS/JS frontend + Firebase (Auth/Firestore)**.

---

## 1. Requirements Analysis

### Core requirement summary

| # | Requirement | Source | Priority |
|---|-------------|--------|----------|
| R1 | Student profiles with department, year, interests | PLAN §6.1 | Must (MVP) |
| R2 | Searchable event database | PLAN §6.2 | Must (MVP) |
| R3 | Rule-based interest matching + scoring | PLAN §6.3 | Must (MVP) |
| R4 | Event discovery with filters (category, date, keyword) | PLAN §6.4 | Must (MVP) |
| R5 | Save events + register (dedup, capacity, deadline enforced server-side) | PLAN §6.5 | Must (MVP) |
| R6 | In-app notifications/reminders | PLAN §6.6 | Should (post-MVP) |
| R7 | Admin dashboard with role-based access | PLAN §6.7 | Must (MVP) |
| R8 | Auth (student + admin) with backend token verification | PLAN §13 | Must (MVP) |

### Scoring rules (recommendation engine — PLAN §6.3)

- Category match: **+3**
- Each matching tag: **+2**
- Department/year relevance: **+1**
- Exclude: past events, cancelled events, draft (unpublished) events
- Sort: match score DESC, then date ASC

### Key constraints / risks

- All authorization **must** be enforced server-side (never trust frontend visibility).
- Registration uniqueness: `(eventId, uid)` pair must be unique — enforce with a Firestore composite of transaction/batch writes to prevent race conditions.
- Capacity and registration deadline must be checked in the same transaction as the registration write.
- Secrets only in `.env` (commit `.env.example`, never `.env` — see [.gitignore](.gitignore)).
- MVP = rule-based matching only; no AI/NLP until the basic flow works.

---

## 2. Phase 1 — Requirements & Setup

- [ ] Confirm MVP scope: R1–R5, R7, R8 (R6 deferred)
- [ ] Create GitHub repo `campus-event-recommendation-bot`
- [ ] Scaffold `backend/` with Flask (`app.py`, `config.py`, `routes/`, `services/`)
- [ ] Scaffold `frontend/` (HTML/CSS/JS)
- [ ] Create `backend/requirements.txt` (flask, firebase-admin, python-dotenv)
- [ ] Create `.env.example` and `.gitignore`
- [ ] Create Firebase project; enable Auth + Firestore; store service-account key path in `.env`

## 3. Phase 2 — Database & Auth

- [ ] Define Firestore collections: `users`, `events`, `registrations` (PLAN §7)
- [ ] Write Firestore Security Rules (students read published events / own docs; admins write events)
- [ ] Implement student sign-in (Firebase Auth token verification middleware in Flask)
- [ ] `GET/PUT /api/profile` — student profile + interests
- [ ] Admin role check middleware (custom claim or `users` doc role field)

## 4. Phase 3 — Event Management

- [ ] `POST /api/admin/events` — create event with validation (dates, capacity, deadline)
- [ ] `PUT /api/admin/events/<event_id>` — edit
- [ ] `POST /api/admin/events/<event_id>/cancel` — cancel
- [ ] Event status lifecycle: `draft → published → cancelled`
- [ ] `GET /api/events` with filters: category, date range, department, keyword
- [ ] `GET /api/events/<event_id>` — details

## 5. Phase 4 — Recommendation Engine

- [ ] `services/recommender.py` — scoring per rules above (pure-Python, unit-testable)
- [ ] Exclude past / cancelled / draft events
- [ ] Boost events with open registration
- [ ] `GET /api/recommendations` — return ranked list for signed-in student
- [ ] Tune weights after testing (make weights config values, not hard-coded)

## 6. Phase 5 — Registration & Saved Events

- [ ] `POST /api/events/<event_id>/register` — transactional write:
  - [ ] reject past deadline
  - [ ] reject when capacity full
  - [ ] reject duplicate `(eventId, uid)`
- [ ] `GET /api/my-registrations`
- [ ] Registration cancellation + refund of capacity slot
- [ ] Optional: `savedEvents` bookmarks collection

## 7. Phase 6 — Testing & Deployment

- [ ] Unit tests for recommender scoring (`tests/test_recommender.py`, pytest)
- [ ] Unit tests for registration rules (deadline, capacity, dupes)
- [ ] API integration tests (Flask test client with mocked firebase-admin)
- [ ] Verify PLAN §12 checklist items one by one
- [ ] Mobile + desktop layout check
- [ ] Deploy backend (Cloud Run / Firebase Hosting proxy) and frontend
- [ ] Pilot feedback from a small student group

## 8. Definition of Done (MVP)

- [ ] Student can sign in → set interests → see ranked upcoming event recommendations → open details → register
- [ ] Duplicate registration / full capacity / missed deadline are all rejected server-side
- [ ] Admin can create, edit, publish, cancel events with proper authz
- [ ] Students cannot reach admin endpoints
- [ ] PLAN §12 testing checklist fully passes
