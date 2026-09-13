# FYM (Fit Your Macros) — Progress Summary

## Status: Phase 0 through Phase 4 all complete and verified. Every core phase from the original plan is done: schema/auth/day-rollover, the tracker (Mode A), standalone mode (Mode B), the full recommendation engine (macro-fit scoring, eat-out, cook, accept/skip, intent parsing, location), and personalization. Only Phase 5 (polish toward shipping) remains.

---

## 9. Phase 4 — Personalization (COMPLETE AND VERIFIED)

**New table** (`RecommendationEvent`): a deliberately ephemeral accept/skip
signal log - explicitly NOT the permanent raw history that was rejected
during planning. Fed by new `POST /recommendations/eat-out/skip` and
`POST /recommendations/cook/skip` endpoints, plus the existing accept
endpoints (now also logging an event alongside their prior behavior).

**`app/core/personalization.py`**: the periodic summarization job - takes
the current `PreferenceSummary` plus recent events, asks the local LLM
to produce a revised summary that replaces the old one wholesale. Tested
5 cases with fake LLM responses (normal case, a missing-field failure, a
wrong-type failure, truncation to 5 items max, and an empty first-run
case) before ever calling a live model.

**`apply_preference_weighting()`** in `macro_fit.py`: deterministic
keyword-based score nudging - the LLM's job ends once the summary is
generated; scoring time stays completely LLM-free, consistent with
every other scoring decision in this app. Tested 7 cases, including the
single most important property: a genuinely better macro fit still wins
over a worse one even when the worse one is "preferred" - this is a
soft nudge, never a hard override.

**`GET /personalization/summary`** and **`POST /personalization/refresh`**:
view the current summary, or manually trigger the "periodic" job (real
scheduling is deferred to Phase 5, same as the data-refresh pipeline).
Verified the full refresh flow end-to-end with a SQLite stand-in before
testing live: events feed the prompt, the new summary gets saved, and
the processed events get deleted afterward - confirming "running
summary, not raw history" is actually enforced in code, not just
described in a comment.

**Verified live**, for real: skipped a "Fried Chicken Sandwich"
recommendation, accepted a different real item, then ran
`POST /personalization/refresh` against the live Ollama model. It
correctly produced `{"prefers": ["chicken", "sandwiches"], "avoids":
["fried"]}` from just those two real signals - genuinely evidence-based,
not fabricated. `events_processed: 3` confirmed the events were read and
folded in correctly.

Eat-out recommendation scoring now automatically applies this summary
as a soft weighting before ranking results.

---

## 10. What's left: Phase 5 (Polish Toward Shipping)
- Barcode scanning for pantry entry
- Multi-user hardening (data isolation checks beyond what's already
  enforced, rate limits, password reset flows)
- Continuous nutrition data refresh pipeline (re-scrape stale
  restaurants, auto-run eval_nutrition.py, on a schedule)
- Expand restaurant list beyond the initial 10
- iOS + Play Store packaging and submission
- Frontend build in React Native (Expo) - not yet started; everything
  built so far is backend-only, tested via Swagger UI

---

## 1. Nutrition Data Pipeline (built ahead of Phase 3, feeds the schema)

**Goal:** collect structured nutrition data (protein/carb/fat/cal) for the app's
starting restaurant list, entirely with free tools (no paid API keys).

**Restaurants covered (10):** McDonald's, Chick-fil-A, Chipotle, Starbucks,
Wendy's, Taco Bell, Subway, Five Guys, Dairy Queen, Panera Bread.

**Pipeline:**
- `scrape_nutrition.py` — pulls each restaurant's menu from
  `healthyfastfood.org`, parsed **deterministically** (no LLM) using a
  regex-based state machine that reads the site's repeating
  (value, unit) token pairs (cal, protein, carb, fat, sat, trans, net,
  sodium, sugar, fiber, chol, p/cal, p:c ratio per item).
- Falls back to `fastfoodnutrition.org` + a free DuckDuckGo search for any
  restaurant not covered by the primary source (none needed for this batch
  — all 10 resolved via the primary source).
- `eval_nutrition.py` — automated self-consistency check (calories ≈
  4×protein + 4×carb + 9×fat, the Atwater estimate) to catch structural
  parsing bugs, plus a hand-maintained `MANUAL_OVERRIDES` dict for
  corrections found via spot-checking against official sources.

**Result:** 1,353 menu items collected, no LLM/fine-tuning needed for this
batch. 4 corrections applied after spot-checking against Chipotle's and
other restaurants' official nutrition data (Chipotle Brown Rice, Chipotle
Chips, Starbucks Peppermint Mocha Venti, Starbucks Rhythm Kale Chips — all
confirmed as dropped-digit/corrupted-field errors in the source data, not
scraper bugs). ~21 additional flagged items reviewed and confirmed as
expected noise (rounding on tiny portions, alcohol calories not captured
by macros, trace-calorie black coffee).

**Key learnings:**
- The site's numbers and units render as separate text nodes in raw HTML
  (`"580"` then `"cal"`), not combined (`"580cal"`) — this caused an early
  parsing failure that was fixed by adjusting the token-pair logic.
- Deterministic parsing against a well-structured source eliminated the
  need for the originally-planned fine-tuned extraction model for this
  batch of restaurants; that model is now scoped only as a fallback for
  restaurants not covered by a structured source.
- Continuous refresh (re-scrape stale entries, re-run eval automatically)
  was scoped as a Phase 5 task rather than built immediately, since the
  current dataset is fresh and the app isn't live yet.

---

## 2. Phase 0 — Backend Foundation

**Stack:** Python (FastAPI) + PostgreSQL + SQLAlchemy + Alembic.

### Schema (6 tables + Alembic's own `alembic_version`)
- `users` — email, hashed password, `day_start_time` (default midnight).
  Every table below is `user_id`-scoped from day one for future
  multi-tenancy, even though the app is single-user today.
- `daily_targets` — one row per user, persists until explicitly updated.
- `food_logs` — manual or auto-logged entries; `reverted` flag supports
  undo without hard-deleting history.
- `pantry_items` — cook-path ingredients (manual entry now, barcode scan
  writes to the same table later).
- `preference_summaries` — one JSON blob per user, replaced (not
  appended) by the Phase 4 personalization job.
- `restaurant_nutrition` — shared (not user-scoped) cache matching the
  scraper pipeline's output shape, including `attribute_tags` for the
  Phase 3 clarification-filter step.

### Auth
- Email/password registration and login.
- Bcrypt password hashing, JWT access tokens (7-day expiry).
- `GET /auth/me` (protected route) and `PATCH /auth/me/day-start-time`.

### Day-rollover logic
- Per-user configurable `day_start_time` (default 00:00).
- Computed at query time via a logical-day window helper — no midnight
  cron job needed.
- Verified against 3 cases: before rollover, after rollover, and the
  default-midnight case (e.g., a 1am snack with a 4am rollover correctly
  attributes to the previous logical day).

### Verification performed
All of the following were directly tested, not just assumed to work:
- All 6 models import and register correctly with SQLAlchemy.
- Day-rollover logic passes all 3 test cases.
- Password hashing and JWT create/decode round-trip correctly.
- FastAPI app boots and all routes register.
- **End-to-end, live**: Postgres running → Alembic migration created all 7
  tables → registered a real user via `POST /auth/register` → logged in
  via `POST /auth/login` → received a valid JWT → called `GET /auth/me`
  with that token → got back the correct user record (200 response).

### Issues hit and resolved along the way
- `pip`/`python`, `alembic`, and `uvicorn` weren't on the shell's PATH
  after install — resolved by running each via `python3 -m <tool>`.
- `bcrypt` 5.x isn't compatible with `passlib` 1.7.4 — pinned
  `bcrypt==4.0.1`.
- An empty `alembic/versions/` folder doesn't survive being
  zipped/downloaded — had to be recreated manually before migrations
  could be generated.
- `.env` file initially had `DATABASE_URL` and `JWT_SECRET_KEY` on the
  same line with no line break, causing the database name to be parsed
  as `"fym_db JWT_SECRET_KEY=..."` — fixed by putting each variable on
  its own line.
- Wrong Postgres role (`fym_user`, which didn't exist) in the connection
  string — fixed by using the actual `postgres` superuser account.
- First migration attempt recorded an empty revision in
  `alembic_version` without creating any real tables — resolved by
  dropping that tracking table, deleting the stale migration file, and
  regenerating a fresh migration (verified by reading its `upgrade()`
  function before applying it this time).

---

## 3. Phase 1 — Core Tracker (Mode A) — COMPLETE AND VERIFIED

**Endpoints added:**
- `PUT /daily-target` — upsert (create or update; same operation, since the
  client never needs to know whether a target already exists)
- `GET /daily-target`
- `POST /food-log` — create an entry (manual or auto-logged)
- `GET /food-log/today` — all of today's entries (including reverted ones,
  for a history/strikethrough view), respecting the day-rollover window
- `POST /food-log/{entry_id}/revert` — reverts **any** of today's entries,
  not just the most recent one, since a user should be able to undo an
  earlier mistake without reverting everything logged after it
- `GET /food-log/remaining` — the derived Remaining calculation

**Design note:** the Remaining calculation lives in a standalone function
(`app/core/remaining.py`), not embedded in the router — this keeps it
callable directly by Phase 3's recommendation engine later without going
through HTTP, matching the "recommendation engine is decoupled from the
tracker" decision from planning. No new database tables were needed for
Phase 1; it's built entirely on the Phase 0 schema.

**Verification performed:**
- Unit-tested the Remaining calculation logic directly against three
  cases in one scenario: an entry from today counted correctly, an entry
  from before the user's 4am rollover was correctly excluded from
  "today," and a reverted entry was correctly excluded — the resulting
  math (target − logged) came out exact in all cases.
- **End-to-end, live** against the real Postgres database: set a daily
  target (150P/200C/60F/2000cal) via `PUT /daily-target` → logged a food
  entry (30P/0C/5F/165cal) via `POST /food-log` → called
  `GET /food-log/remaining` → got back the exactly correct remaining
  values (120/200/55/1835).

**Issue hit along the way:** none new — Phase 1 didn't require any schema
changes, so no new Alembic migration was needed, and no new environment
setup issues came up.

---

## 4. Phase 2 — Standalone Mode (Mode B) — COMPLETE AND VERIFIED

**Shared budget-splitting math** (`app/core/budget_split.py`): given a
macro budget, returns it in full, as a percentage portion, or split
evenly across N meals. Deliberately pure/stateless (no DB, no user
context) so both Mode A and Mode B call the same function rather than
duplicating this logic — matches the "deterministic math, no LLM" design
decision.

**Endpoints added:**
- `POST /standalone/budget` — no auth, no DB writes at all. User types in
  a macro budget directly and optionally splits it; nothing persists,
  matching Mode B's "no persistence" requirement.
- `POST /standalone/add-to-daily` — the opt-in step: logs what was
  actually eaten as a normal Food Log entry (same table Mode A writes
  to), then returns the resulting Remaining. If no Daily Target exists,
  it doesn't error out — it confirms the entry was logged and returns
  the raw negative usage starting from zero, with a message explaining
  why, per the spec's "keep negative values and flag it to the user"
  requirement.

**Verification performed:**
- Budget-split math tested directly against all 3 modes (full, 50%
  partial, 25% partial, even 4-way split) plus 2 error cases (invalid
  percentage, zero meal count) — all correct.
- The "no daily target" branch in `add-to-daily` tested directly against
  the exact contract `calculate_remaining` returns (`None`) when no
  target row exists — confirmed it falls back to negative raw usage
  rather than erroring or silently doing nothing.
- End-to-end tested live via Swagger against the real Postgres database.

---

## 5. Phase 3 — Recommendation Engine (in progress)

**Macro-fit scoring core** (`app/core/macro_fit.py`): normalized weighted
deviation scoring - each macro's deviation from the target is expressed
as a fraction of the target itself, so a miss matters proportionally
regardless of the target's scale. 0 = exact match, higher = worse fit.
Pure/stateless, no LLM, shared by cook and eat-out paths. Tested against
perfect/close/bad matches, ranking order, a zero-target edge case, and
result limiting - all correct.

**Data loader** (`app/scripts/load_restaurant_nutrition.py`): the
missing link between the scraper (which writes local JSON) and the app
(which reads Postgres) - loads `ok_structured` records into
`restaurant_nutrition`, safely replacing existing rows per restaurant on
re-run rather than duplicating. Tested against realistic data before
running live.

**Eat-out recommendation endpoint** (`POST /recommendations/eat-out`):
takes a macro budget, scores every cached menu item (optionally filtered
to one restaurant) against it, returns ranked results. Filters out any
item with incomplete macro data rather than scoring it unfairly.

**Verified live, end to end, with real data:** loaded all ~1,353 scraped
menu items into Postgres, then queried with a target budget of
28g protein / 40g carb / 6g fat / 320cal against Chick-fil-A's menu. The
Grilled Chicken Sandwich (28P/41C/6F/320cal - an almost exact match)
correctly won with a fit score of 0.0071, with the rest of the ranked
list making clear sense (next-best protein match, then progressively
worse fits as the macro profile diverges). This is the first time the
full pipeline - real scraped data, deterministic scoring, and a live
API - has worked together end to end.

**Still to build in Phase 3:**
- Location/radius lookup (places API) for the eat-out path
- Free-text intent parsing (LLM) + broad-vs-specific detection
- Clarification flow (category→attribute lookup table, keyword→tag
  scraper tagging) for filtering by spice level, cooking style, etc.

---

## 6. Phase 3 continued — Pantry CRUD, Cook Path, and Accept Endpoints (COMPLETE AND VERIFIED)

**Pantry CRUD** (`app/routers/pantry_item.py`): full create/list/update
(partial)/delete, same pattern as Food Log CRUD from Phase 1. Tested the
ownership check (one user can't see/modify another's pantry - important
given the multi-tenant-ready design) and the partial-update logic
(`PATCH` only changes fields actually sent) directly - both correct.

**Cook path — recipe generation via local LLM** (`app/core/ollama_client.py`,
`app/core/recipe_generation.py`): this is the 4th LLM use case in the
app, added deliberately as a scope decision (weighed against a curated
recipe-database alternative) since the original spec called for
step-by-step recipes adapted to available pantry ingredients, which is
generation, not just matching.

**Critical design principle, consistent with the rest of the app:** the
LLM only picks ingredients and writes cooking steps - it never does the
macro arithmetic. Every protein/carb/fat/cal number in the response is
computed deterministically from the pantry items' own known values
(scaled proportionally to however much of each was actually used), never
trusted from whatever the model claims. This let the system safely
reject: a recipe asking for more of an ingredient than is actually in
the pantry, a recipe referencing an ingredient not in the pantry at all,
and an empty ingredient selection - all tested directly with fake LLM
responses before ever calling a live model, alongside a markdown-fence-
wrapped JSON response (a known LLM quirk) parsing correctly.

**Verified live** against a real local Ollama (llama3.1) instance and a
real 4-item pantry (chicken breast, brown rice, broccoli, olive oil):
generated an actual "Chicken and Broccoli Stir Fry" recipe with real
steps and correctly computed macros from the selected quantities.

**Accept endpoints** (closing the loop from recommendation back to the
tracker, using the `FoodLog.source = RECOMMENDED` field that had been
unused since Phase 0):
- `POST /recommendations/eat-out/accept` — takes only a
  `restaurant_nutrition_id`; looks up that item's real macros fresh from
  the database (never trusts client-submitted macros) and logs it.
- `POST /recommendations/cook/accept` — takes the recipe name and which
  pantry items/quantities were used (no macros from the client at all);
  recomputes the totals the same deterministic way as generation time,
  deducts those quantities from the pantry, and logs the entry.
  Tested the **all-or-nothing guarantee** directly: if any ingredient in
  the list fails validation, nothing gets mutated - not even earlier
  ingredients in the same request that would have succeeded on their own.

**Verified live, end to end:** accepted both a real eat-out recommendation
(Subway item, logged with source `recommended`) and the real generated
cook recipe above (pantry quantities correctly deducted, recipe logged
with macros exactly matching what generation computed).

**Still to build in Phase 3:**
- Location/radius lookup (places API) for the eat-out path

---

## 7. Phase 3 continued — Intent Parsing + Clarification Flow (COMPLETE AND VERIFIED)

**Two deterministic lookup tables** (`app/core/category_attributes.py`),
matching the original design decision to keep anything with a small,
known answer space out of the LLM's hands:
- `CATEGORY_ATTRIBUTES` — category → clarifying attributes shown as
  tappable UI options (e.g. burger → spice level, cooking style).
- `KEYWORD_TAG_MAP` + `derive_tags_from_name()` — scans a menu item's
  name for known keywords and derives attribute tags deterministically.
  Tested against 7 realistic menu item names (e.g. "Crispy Chicken BLT"
  → `['chicken', 'fried']`) - all correct. Feeds the
  `attribute_tags` column on `restaurant_nutrition` that's existed since
  Phase 0 but was unused until now.

**LLM-based intent parsing** (`app/core/intent_parsing.py`): the
genuinely open-ended piece — classifies free text like "I want a
burger" into a category, a broad-vs-specific signal, and any attributes
already mentioned. Tested 5 cases with fake LLM responses (broad
request, already-specific request with attributes captured, markdown-
wrapped JSON, a missing-required-field failure, and an omitted-optional-
field default) before ever calling a live model.

**`POST /intent/parse`**: combines both — parses intent, then only
surfaces clarification options for attributes the user hasn't already
specified. Tested 4 scenarios directly: a fully broad request gets both
attributes back, a partially-specific request ("spicy burger") correctly
asks only about the remaining attribute (cooking style), a fully
specific request needs no clarification at all, and a category with no
defined attribute set fails gracefully rather than erroring.

**Verified live** against real Ollama calls: "I want a burger" correctly
came back broad with both clarification questions populated exactly as
designed; "I want a spicy grilled chicken sandwich" correctly came back
specific with attributes captured and no clarification needed.

One known rough edge, not yet fixed: the live model sometimes uses
attribute key names that don't exactly match the lookup table's keys
(e.g. `spice` instead of `spice_level`). This didn't cause an incorrect
result in testing since it only matters when a request is broad AND
partially specific, but it's a prompt-tuning item worth tightening later
(constrain the model to only use exact keys from the known attribute
list).

**Still to build in Phase 3:**
- Location/radius lookup (places API) for the eat-out path

---

## 8. Phase 3 continued — Location/Radius Lookup (COMPLETE AND VERIFIED — Phase 3 now fully done)

**Design decision:** chose OpenStreetMap's Overpass API over Google
Places or Foursquare, since it requires no API key, no signup, and no
billing account ever — the only option matching this project's
consistent "free tools only" principle without any friction. Since
nutrition data is scraped per chain (not per individual store location),
this only needed to answer "which chains I have data for have a real
location near the user" - not full menu/place data.

**`app/core/geo.py`**: haversine great-circle distance, pure math, no
external calls. Tested against 3 known real-world distances (San
Jose↔SF ~68km, NYC↔London ~5570km, same-point = 0) — all matched closely.

**`app/core/overpass_client.py`**: queries Overpass for nearby
restaurant/fast-food/cafe nodes, matches results against the chains
already in the `restaurant_nutrition` table (queried dynamically -
no separate hardcoded chain-name list needed), deduplicates to the
nearest location per chain, and computes distance via the haversine
function above. Tested exact-name matching, substring matching (handles
"McDonald's - Main St"), correct deduplication to the nearest of
multiple candidate locations, and graceful skipping of malformed OSM
data (missing coordinates, missing name tag) - all correct, using fake
Overpass responses before ever calling the live API.

**Updated `POST /recommendations/eat-out`**: when `lat`/`lon` are
provided, results are now filtered to only chains with a real nearby
location (overriding a plain `restaurant_id` filter), and each result
includes its `distance_km`. Simulated the full combined flow end-to-end
with fake data (a non-nearby chain correctly excluded, nearby chains
correctly included and scored) before testing live.

**Issue hit and resolved:** the first live call returned `406 Not
Acceptable` from Overpass - a known gotcha where the API blocks
requests using Python's default `User-Agent` string (since many abusive
scripts use it unmodified). Fixed by sending a proper identifying
`User-Agent` header, which Overpass's own usage policy explicitly
requests anyway.

**Verified live**, for real: a request from real coordinates correctly
returned a real nearby Subway (0.2km) and Starbucks (0.04km), both
scored against the macro budget and ranked - confirming the full chain
works end-to-end with a genuine third-party service, not just
simulated data.

---

## 9. Next: Phase 4 (Personalization)
- Track accept/skip events against recommendations
- Periodic (e.g. weekly) LLM job: current `PreferenceSummary` + recent
  accept/skip window → new summary (replace, not append)
- Feed the summary into the macro-fit scorer as a soft weighting term -
  never a hard filter, per the original design decision
