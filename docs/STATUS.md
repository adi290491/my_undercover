# Status

The pilot is being built from `docs/PLAN.md`. Phases done: 2 of 6.

## What's built

- `backend/`: FastAPI on SQLite. The database `backend/undercover.db` is seeded from `data/` on first start (never from `data/evals/` or `data/security/`). Read routes for claims, policies, plans, claim history, the policy wording, the agent's instructions (`backend/instructions.md`) and handlers. Workflow routes to start a claim, record steps, record a decision, pay and sign off. A claim is `waiting`, `in_progress`, `awaiting_signoff` or `decided`, and a payout over $1,000 (from `data/company.json`) can only be paid by a handler's sign-off.
- `agent/`: the skeleton entry point `run(claim_id, thread_id)`.
- `dashboard/`: one page that shows whether the backend is up.
- `e2e/`: one test of that page.

## How to run it

- `npm run dev` starts the backend on port 8000 and the dashboard on port 5173.
- `uv run -m backend.seed` rebuilds the database, with every claim waiting.
- `npm run check` runs every check.
