# Plan: the claims pilot

This plan builds the pilot in `docs/SPEC.md`: a backend that holds the claims queue, the UnderCover Agent that decides claims through the backend's API, and a dashboard where handlers watch the queue, read decisions, follow the agent step by step, read its instructions and sign off large payouts.

It is built in six phases. Each one leaves the product working and checked, and the next builds on it.

## Key decisions

- **The backend is the only door.** The agent never reads `data/` or the database. It reaches claims, policies, claim history, the policy wording and its own instructions through the backend's API, as `docs/TECH_STACK.md` asks. That makes the backend the one place that enforces the rules.
- **The $1,000 rule is enforced in the backend, not the prompt.** `pay_claim` refuses any payment over the limit until a handler has signed off, whatever the agent does. The prompt mentions the rule, but nothing depends on the model following it.
- **The answer key is never loaded.** The seed reads only the queue's records. It never reads `data/evals/` or `data/security/`, so no endpoint can serve them. A test checks that.
- **The agent sees only what it needs.** Claim history comes from its own operation, which returns past claims without the customer's email, phone, address or date of birth.
- **The policy wording is the reference, the claims manual is left out**, as the spec says for the pilot. The agent's instructions live in the backend (`backend/instructions.md`), so the dashboard and the agent read the same text.
- **Steps are recorded by the agent's runner, not by the model.** The entry point streams the agent's updates and posts each tool call and result to the backend. The model can't skip or invent a step, and the dashboard polls the claim to show them while it works.
- **The claim states** are `waiting`, `in_progress`, `awaiting_signoff` and `decided`. The data's `open` becomes `waiting` on seeding. Declined and referred claims are `decided`. An approval of $1,000 or less is paid straight away and becomes `decided`. An approval over $1,000 waits at `awaiting_signoff` until a handler signs off, which makes the payment.
- **Nothing new to install.** Everything needed (FastAPI, SQLite from the standard library, LangChain, httpx, React, Vite, Playwright) is already in `pyproject.toml` and `package.json`. The dashboard uses a small hash router rather than adding a routing library.

## The API

Every operation has an `operation_id`, a one-line docstring and no optional inputs.

| Operation | Route | Used by |
|---|---|---|
| `health` | `GET /api/health` | dashboard |
| `list_claims` | `GET /api/claims` | dashboard |
| `get_claim` | `GET /api/claims/{claim_id}` | agent, dashboard |
| `get_policy` | `GET /api/policies/{policy_id}` | agent, dashboard |
| `get_plan` | `GET /api/plans/{plan}` | agent |
| `get_claim_history` | `GET /api/customers/{customer_id}/claims` | agent, dashboard |
| `get_policy_wording` | `GET /api/policy-wording` | agent |
| `get_instructions` | `GET /api/instructions` | agent, dashboard |
| `list_handlers` | `GET /api/handlers` | dashboard |
| `start_claim` | `POST /api/claims/{claim_id}/start` | agent runner |
| `add_step` | `POST /api/claims/{claim_id}/steps` | agent runner |
| `list_steps` | `GET /api/claims/{claim_id}/steps` | dashboard |
| `record_decision` | `POST /api/claims/{claim_id}/decision` | agent |
| `pay_claim` | `POST /api/claims/{claim_id}/payment` | agent |
| `sign_off` | `POST /api/claims/{claim_id}/sign-off` | dashboard |
| `release_claim` | `POST /api/claims/{claim_id}/release` | agent runner, when a run fails |
| `run_agent` | `POST /api/claims/{claim_id}/run` | dashboard |

A decision holds `decision` (`approve`, `decline` or `refer`), `payout`, `reason` (two or three sentences) and `policy_section` (such as "Section 3, Trip Delay"). `pay_claim` takes the amount, and the amount must match the approved payout.

## Phase 1: Records and the read API

**Builds:** a SQLite database seeded from `data/`, and the read operations above. The database file is `backend/undercover.db`, created on startup when missing and ignored by git; `uv run -m backend.seed` rebuilds it from scratch. Tests run against a fresh database in a temporary folder.

**Why first:** everything else, the agent and the dashboard alike, reads these records. Getting the data and its shape right first means later phases build on something fixed.

**Success criteria:**

- [x] `uv run -m backend.seed` creates `backend/undercover.db` with 25 claims, all `waiting`
- [x] `GET /api/claims` returns 25 claims, each with id, claim type, customer name, amount claimed, submitted date and status
- [x] `GET /api/claims/CLM-1001` returns the story, items, documents and amount claimed ($420.00)
- [x] `GET /api/policies/POL-2001` returns the Premium plan, the trip and the travelers
- [x] `GET /api/plans/premium` returns the Premium limits, waiting periods and $50 deductible
- [x] `GET /api/customers/CUS-3001/claims` returns CLM-0412 and no email, phone, address or date of birth
- [x] `GET /api/policy-wording` returns the text of `data/policy_wording.md`
- [x] `GET /api/instructions` returns the text of `backend/instructions.md`
- [x] An unknown claim, policy, plan or customer returns 404
- [x] A test confirms the seed never opens `data/evals/` or `data/security/`
- [x] A test confirms every route has an `operation_id`, a one-line docstring and no optional inputs
- [x] `npm run check:python` passes with coverage of 80% or more

## Phase 2: The claim workflow and the payment rule

**Builds:** the operations that change a claim: `start_claim`, `add_step`, `list_steps`, `record_decision`, `pay_claim` and `sign_off`, with the state rules enforced in the backend.

**Why next:** the $1,000 rule is the one hard rule in the spec, and it has to hold no matter what the agent does. Building and testing it before the agent exists proves it doesn't rely on the agent behaving.

**Success criteria:**

- [x] `start_claim` moves a `waiting` claim to `in_progress` and records its thread id; on a claim that is not `waiting` it returns 409
- [x] `add_step` stores a step with a time, a kind (`tool_call`, `tool_result`, `message` or `error`) and text; `list_steps` returns them in order
- [x] `record_decision` with `decline` or `refer` and payout 0 moves the claim to `decided`
- [x] `record_decision` rejects a decline or refer with a payout, an approve with no payout, and a reason longer than three sentences, with 422
- [x] An approve of $1,000 or less leaves the claim `in_progress` until `pay_claim` with that amount, which records the payment and moves it to `decided`
- [x] An approve over $1,000 moves the claim to `awaiting_signoff`
- [x] `pay_claim` over $1,000 with no sign-off returns 403 and records no payment
- [x] `pay_claim` with an amount that doesn't match the approved payout returns 409
- [x] `sign_off` with a handler id records the handler, makes the payment and moves the claim to `decided`; with an unknown handler it returns 404; on a claim not awaiting sign-off it returns 409
- [x] `GET /api/claims/{id}` includes the decision, the payment and the sign-off when there are any
- [x] `npm run check:python` passes

## Phase 3: The UnderCover Agent

**Builds:** the agent in `agent/`, on `create_agent` with OpenRouter and the model in `MODEL_NAME` or `openai/gpt-6-luna` at low reasoning effort. `run(claim_id, thread_id)` loads the instructions from `get_instructions`, calls `start_claim`, and streams the agent, posting each tool call and result as a step. Its tools are thin wrappers on the API: `get_claim`, `get_policy`, `get_plan`, `get_claim_history`, `get_policy_wording`, `record_decision` and `pay_claim`. It has no tool for sign-off. `backend/instructions.md` tells it how to work a claim: read everything, decide from the policy wording, work out the payout with the plan's limits and deductible, explain in two or three sentences with the section, and pay only when the payout is $1,000 or less. `uv run -m agent CLM-1001` runs it on one claim from the command line.

**Why here:** with the backend's rules in place, the agent is the only new moving part, and the stub-model tests can drive it against the real API.

**Success criteria:**

- [x] With a stub model, a test runs a claim through `get_claim`, `get_policy`, `get_policy_wording`, `record_decision` and `pay_claim`, and the claim ends `decided` with the steps recorded
- [x] With a stub model that approves $1,500 and then calls `pay_claim`, the payment is refused, the refusal is a recorded step and the claim ends `awaiting_signoff`
- [x] A test confirms the agent's tools are exactly the seven above, with no sign-off tool
- [x] A test confirms the system prompt is the text from `get_instructions`
- [x] The model choice tests still pass for the default and for `MODEL_NAME`
- [x] `uv run -m agent CLM-1001` with the real model ends with CLM-1001 decided, a reason of two or three sentences and a policy section (one real call, a few cents)
- [x] `npm run check:python` passes

## Phase 4: Running the agent from the backend

**Builds:** `run_agent`, which starts the agent on a waiting claim as a background task with a new thread id and returns at once, so the dashboard can start a claim and watch it. `uv run -m agent queue` works every waiting claim in turn from the command line.

**Why here:** the dashboard needs a way to start the agent, and the queue command is how the team works the whole queue straight through.

**Success criteria:**

- [x] With a stub model, `POST /api/claims/CLM-1001/run` returns 202 with the thread id, and the claim moves to `in_progress` and then `decided`
- [x] `run_agent` on a claim that isn't `waiting` returns 409
- [x] If the agent fails partway, the failure is recorded as a step and the claim goes back to `waiting` with any unpaid decision dropped, so it can be run again
- [x] With a stub model, `uv run -m agent queue` decides every waiting claim in the seeded queue and leaves a claim already in progress alone
- [x] `npm run check:python` passes

## Phase 5: The dashboard

**Builds:** three pages in `dashboard/`, in the brand's fonts, colors and light and dark surfaces.

- **Queue:** every claim with its id, customer, type, amount claimed, submitted date and a colored state badge (waiting Cerulean, in progress Marigold, awaiting sign-off Coral, decided Sea Green), with counts for each state.
- **Claim:** the story, items, documents, policy and claim history, the agent's decision with payout, reasons and policy section, the payment, and a Run agent button on a waiting claim.
- **Instructions:** the agent's instructions, read only.

**Why here:** with the backend and the agent working, the dashboard shows real data from the start.

**Success criteria:**

- [x] Vitest tests cover the queue, the claim page and the instructions page against stubbed fetches
- [x] With `npm run dev` running, the Playwright MCP server shows the queue with 25 claims and their state counts, in both light and dark mode
- [x] The Playwright MCP server shows CLM-1001 with its story, items, documents, policy and history, and money as $420.00
- [x] The Playwright MCP server shows the instructions page with no way to edit them
- [x] The page has no horizontal scroll at phone width
- [x] `npm run check:ts` passes with coverage of 80% or more

## Phase 6: Live steps, sign-off and end-to-end tests

**Builds:** the claim page polls the claim and its steps while the agent works and shows each step as it happens. A claim awaiting sign-off shows the payout, a handler picker and a Sign off button. The Playwright tests run the full flow with a stub model, chosen by `MODEL_NAME=stub` in the test server only, so they never call a model. They start their own backend, database and dashboard on other ports, so they never touch the dev servers. `docs/STATUS.md` describes what's built and how to run it.

**Why last:** this joins the agent, the backend and the dashboard, and the end-to-end tests check the whole pilot together.

**Success criteria:**

- [x] A Playwright test runs the agent on a claim from the dashboard and sees the steps appear and the claim reach decided
- [x] A Playwright test takes a claim to awaiting sign-off, signs off as a handler and sees it decided with the payment and the handler's name
- [x] A Playwright test opens the instructions page
- [x] The Playwright MCP server shows a real run on one claim with its steps appearing live and its decision and reasons at the end
- [x] `docs/STATUS.md` says what's built and how to run it
- [x] `npm run check` passes: ruff, pyright, pytest, ESLint, Prettier, tsc, vitest and Playwright

## Not in this plan

- Scoring the agent against `data/evals/`. The spec keeps the handlers' decisions for checking the agent's work, and the labs and later builds do that; nothing in the pilot reads them.
- The claims manual, sign-in, real payments and messages to customers, as the spec says.
