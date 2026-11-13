# Status

The pilot in `docs/PLAN.md` is being built. Phases 1 and 2 of 6 are done.

## What's built

- `backend/`: FastAPI on SQLite. The database (`backend/undercover.db`, or the file in `UNDERCOVER_DB`) is seeded from `data/` on first start, never from `data/evals/` or `data/security/`. Read routes for claims, policies, plans, claim history (without contact details), the policy wording, the agent's instructions (`backend/instructions.md`) and handlers.
- `agent/`: still the skeleton, with one tool that checks the backend.
- `dashboard/`: React pages in the brand's fonts and colors, light and dark, on hash routes. The queue (`#/`) has a count for each claim state and a row for each claim, which become cards at phone width. Each claim's page (`#/claims/CLM-1001`) shows the story, items, documents, policy and claim history. The agent's instructions (`#/instructions`) are read only.
- `tests/`: the unit tests, in `tests/backend/`, `tests/agent/` and `tests/dashboard/`.
- `e2e/`: Playwright tests of the queue, a claim's page and the instructions. It starts its own backend on port 8001 with a freshly seeded database (`e2e/e2e.db`) and its own dashboard on port 5174.

## How to run it

- `npm run dev` starts the backend on port 8000 and the dashboard on http://localhost:5173.
- `uv run -m backend.seed` rebuilds the database, with every claim waiting.
- `npm run check` runs every check.
