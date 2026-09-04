# FYM Backend (Phase 0)

FastAPI + PostgreSQL backend. Phase 0 covers: full schema, auth, and
day-rollover logic.

## What's here

**Models** (`app/models/`):
- `User` — single-user today, but `user_id`-keyed everywhere for future multi-tenancy. Includes `day_start_time` (default midnight).
- `DailyTarget` — one row per user, persists until updated.
- `FoodLog` — manual or auto-logged entries; `reverted` flag supports undo without hard-deleting history.
- `PantryItem` — cook-path ingredients (manual entry now, barcode scan later writes to the same table).
- `PreferenceSummary` — one JSON blob per user, replaced (not appended) by the Phase 4 personalization job.
- `RestaurantNutrition` — shared (not user-scoped) cache of scraped menu data, matches the shape `scrape_nutrition.py`/`eval_nutrition.py` already produce.

**Core** (`app/core/`):
- `config.py` — settings from environment variables.
- `database.py` — SQLAlchemy engine/session.
- `security.py` — password hashing (bcrypt) + JWT create/decode. Both verified working.
- `day_rollover.py` — computes the logical-day window from a user's `day_start_time`, no midnight cron job needed. Verified against 3 edge cases including the "1am snack with 4am rollover" case.
- `deps.py` — `get_current_user` FastAPI dependency for protected routes.

**Auth endpoints** (`app/routers/auth.py`):
- `POST /auth/register`
- `POST /auth/login` (returns JWT)
- `GET /auth/me`
- `PATCH /auth/me/day-start-time`

## Setup

```bash
cd fym_backend
pip install -r requirements.txt --break-system-packages
```

You'll need a running Postgres instance. Set the connection string via
environment variable or a `.env` file (see `app/core/config.py` for the
default/expected format):

```
DATABASE_URL=postgresql://fym_user:fym_pass@localhost:5432/fym_db
JWT_SECRET_KEY=<generate something random for real use>
```

## Run migrations

```bash
alembic revision --autogenerate -m "Initial schema"
alembic upgrade head
```

This creates all 6 tables in Postgres based on the SQLAlchemy models.

## Run the server

```bash
uvicorn app.main:app --reload
```

Visit `http://localhost:8000/docs` for interactive API docs (Swagger UI) —
you can register a user, log in, and hit the protected `/auth/me` endpoint
directly from there to confirm everything works end-to-end.

## What's verified vs. not yet

**Verified in this environment:**
- All 6 models import and register with SQLAlchemy's metadata correctly.
- Day-rollover logic passes 3 test cases (before/after rollover, default midnight).
- Password hashing and JWT create/decode round-trip correctly.
- FastAPI app boots and all routes register as expected.

**Not yet verified (needs a real Postgres instance, which this sandbox doesn't have):**
- Actual migration run against a live database.
- End-to-end register → login → protected-route flow over HTTP.

Worth running through those once you've got Postgres running locally, just
to confirm the last mile works — everything up to that point has been
tested directly.

## Next steps (Phase 1)

Daily Target CRUD, Food Log CRUD, and the derived Remaining calculation —
all of which build directly on this schema and the day-rollover helper.
