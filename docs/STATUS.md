# Status

The pilot in `docs/PLAN.md` is being built. Phases 1 to 4 of 6 are done.

## What's built

- `backend/`: FastAPI on SQLite. The database (`backend/undercover.db`, or the file in `UNDERCOVER_DB`) is seeded from `data/` on first start, never from `data/evals/` or `data/security/`. Read routes for claims, policies, plans, claim history (without contact details), the policy wording, the agent's instructions (`backend/instructions.md`) and handlers. Workflow routes to start a claim, record steps, record a decision, pay, sign off and release a claim after a failed run.
- Claim states: `waiting`, `in_progress`, `awaiting_signoff` and `decided`. A decline or referral is decided at once. An approval of $1,000 or less is decided once it is paid. An approval over $1,000 (the limit in `data/company.json`) waits for a handler's sign-off, and `pay_claim` refuses it with 403 until then; the sign-off makes the payment. A decision cites a section of the policy wording by number, and its reason must be two or three sentences.
- `agent/`: the UnderCover Agent, `run(claim_id, thread_id)`, on LangChain's `create_agent` with OpenRouter, using `openai/gpt-6-luna` at low reasoning effort or the model in `MODEL_NAME`. It reads its instructions from the backend and has seven tools that call the API: `get_claim`, `get_policy`, `get_plan`, `get_claim_history`, `get_policy_wording`, `record_decision` and `pay_claim`. It has no sign-off tool. Each tool call, result and message is posted to the backend as a step, and a refused call is recorded as an error the agent reads. A run that fails or ends unfinished records why and puts the claim back to `waiting`. `MODEL_NAME=stub` swaps in a scripted model that approves each claim in full, for tests. The agent finds the backend at `BACKEND_URL`, or port 8000.
- `dashboard/`: React pages in the brand's fonts and colors, light and dark, on hash routes. The queue (`#/`) has a count for each claim state and a row for each claim, which become cards at phone width. Each claim's page (`#/claims/CLM-1001`) shows the decision with the section of the wording it cites, the payment and sign-off, the agent's steps grouped by run, the story, items, documents, policy and claim history. The agent's instructions (`#/instructions`) are read only.
- `tests/`: the unit tests, in `tests/backend/`, `tests/agent/` and `tests/dashboard/`.
- `e2e/`: Playwright tests of the queue, a claim's page and the instructions. It starts its own backend on port 8001 with a freshly seeded database (`e2e/e2e.db`) and its own dashboard on port 5174.

## How to run it

- `npm run dev` starts the backend on port 8000 and the dashboard on http://localhost:5173.
- `uv run -m backend.seed` rebuilds the database, with every claim waiting.
- `uv run -m agent CLM-1001` runs the agent on one claim. The backend must be running.
- `npm run check` runs every check.

## Notes

- `.env` doesn't override variables already set in the environment, so `MODEL_NAME=stub` on the command line wins over a `MODEL_NAME` in `.env`.
- After pulling a change to the database's tables, run `uv run -m backend.seed` to rebuild it.
