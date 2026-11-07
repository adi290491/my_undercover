# Status

The pilot in `docs/PLAN.md` is built: all six phases are done.

## What's built

- `backend/`: FastAPI on SQLite. The database (`backend/undercover.db`, or the file in `UNDERCOVER_DB`) is seeded from `data/` on first start, never from `data/evals/` or `data/security/`. Read routes for claims, policies, plans, claim history (without contact details), the policy wording, the agent's instructions (`backend/instructions.md`) and handlers. Workflow routes to start a claim, record steps, record a decision, pay, sign off, release a claim after a failed run and run the agent in the background.
- Claim states: `waiting`, `in_progress`, `awaiting_signoff` and `decided`. A decline or referral is decided at once. An approval of $1,000 or less is decided once the agent pays it. An approval over $1,000 (the limit in `data/company.json`) waits for a handler's sign-off, and `pay_claim` refuses it with 403 until then; the sign-off makes the payment.
- `agent/`: the UnderCover Agent, `run(claim_id, thread_id)`, on LangChain's `create_agent` with OpenRouter, using `openai/gpt-6-luna` at low reasoning effort or the model in `MODEL_NAME`. It reads its instructions from the backend and has seven tools that call the API: `get_claim`, `get_policy`, `get_plan`, `get_claim_history`, `get_policy_wording`, `record_decision` and `pay_claim`. It has no sign-off tool. Each tool call and result is posted to the backend as a step. If a run fails, the failure is recorded and the claim goes back to `waiting`. `MODEL_NAME=stub` swaps in a scripted model that approves each claim in full, for tests.
- `dashboard/`: React pages in the brand's fonts and colors, light and dark. The queue shows counts by status and refreshes every two seconds. Each claim's page shows the story, items, documents, policy, claim history, decision, payment and sign-off, with a Run the agent button. While the claim is waiting or in progress, the page follows the agent's steps live. A claim awaiting sign-off has a handler picker and a Sign off and pay button. The agent's instructions are read only. Pages are hash routes: `#/`, `#/claims/CLM-1001`, `#/instructions`.
- `e2e/`: Playwright tests of the queue, a run that is paid, a run that waits for sign-off and is signed off, and the instructions. They start their own backend on port 8001 with a fresh database and the stub model, and their own dashboard on port 5174.

## How to run it

- `npm run dev` starts the backend on port 8000 and the dashboard on http://localhost:5173.
- `uv run -m backend.seed` rebuilds the database, with every claim waiting.
- `uv run -m agent CLM-1001` runs the agent on one claim, and `uv run -m agent queue` works every waiting claim in turn. The backend must be running.
- `npm run check` runs every check.

## Notes

- `.env` no longer overrides variables already set in the environment, so the end-to-end tests' `MODEL_NAME=stub` wins over a `MODEL_NAME` in `.env`.
- Not built, as the spec says: the claims manual, sign-in, real payments and messages to customers. Nothing scores the agent against `data/evals/` yet.
