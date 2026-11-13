# Status

The pilot in `docs/PLAN.md` is being built. Phase 1 of 6 is done.

## What's built

- `backend/`: FastAPI on SQLite. The database (`backend/undercover.db`, or the file in `UNDERCOVER_DB`) is seeded from `data/` on first start, never from `data/evals/` or `data/security/`. Routes: `health`, `list_claims` and `get_claim`.
- `agent/`: still the skeleton, with one tool that checks the backend.
- `dashboard/`: the queue page in the brand's fonts and colors, light and dark, with a count for each claim state and a row for each claim. At phone width the rows become cards.
- `tests/`: the unit tests, in `tests/backend/`, `tests/agent/` and `tests/dashboard/`.
- `e2e/`: a Playwright test of the queue. It starts its own backend on port 8001 with a freshly seeded database (`e2e/e2e.db`) and its own dashboard on port 5174.

## How to run it

- `npm run dev` starts the backend on port 8000 and the dashboard on http://localhost:5173.
- `uv run -m backend.seed` rebuilds the database, with every claim waiting.
- `npm run check` runs every check.
