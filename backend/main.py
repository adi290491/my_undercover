"""The UnderCover backend."""

import sqlite3
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, FastAPI, HTTPException

from agent.main import run
from backend import claims, db
from backend.models import (
    Claim,
    ClaimState,
    ClaimSummary,
    DecisionRequest,
    Handler,
    PastClaim,
    PaymentRequest,
    Plan,
    Policy,
    ReleaseRequest,
    RunStarted,
    SignOffRequest,
    StartRequest,
    Step,
    StepRequest,
    Text,
)

INSTRUCTIONS = Path(__file__).parent / "instructions.md"


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    db.ensure()
    yield


app = FastAPI(title="UnderCover", lifespan=lifespan)


@app.get("/api/health", operation_id="health")
def health() -> dict[str, str]:
    """Check that the backend is running."""
    return {"status": "ok"}


@app.get("/api/claims", operation_id="list_claims")
def list_claims() -> list[ClaimSummary]:
    """List every claim in the queue with where it stands."""
    with db.connect() as conn:
        return [ClaimSummary.model_validate(c) for c in claims.queue(conn)]


@app.get("/api/claims/{claim_id}", operation_id="get_claim")
def get_claim(claim_id: str) -> Claim:
    """Get one claim in full, with its story, items, documents and status."""
    with db.connect() as conn:
        return Claim.model_validate(claims.find(conn, claim_id))


def lookup(table: str, key: str, value: str, missing: str) -> dict[str, Any]:
    """Return one record, or raise 404 with the message given."""
    with db.connect() as conn:
        found = db.record(conn, table, key, value)
    if found is None:
        raise HTTPException(404, missing)
    return found


@app.get("/api/policies/{policy_id}", operation_id="get_policy")
def get_policy(policy_id: str) -> Policy:
    """Get a policy: its plan, add-ons, purchase date, trip and travelers."""
    return Policy.model_validate(
        lookup("policies", "policy_id", policy_id, f"There is no policy {policy_id}.")
    )


@app.get("/api/plans/{plan}", operation_id="get_plan")
def get_plan(plan: str) -> Plan:
    """Get a plan's limits, waiting periods and deductible, such as premium."""
    return Plan.model_validate(
        lookup("plans", "plan", plan, f"There is no plan {plan}.")
    )


@app.get("/api/customers/{customer_id}/claims", operation_id="get_claim_history")
def get_claim_history(customer_id: str) -> list[PastClaim]:
    """List a customer's earlier claims, without their contact details."""
    customer = lookup(
        "customers", "customer_id", customer_id, f"There is no customer {customer_id}."
    )
    return [PastClaim.model_validate(c) for c in customer["previous_claims"]]


@app.get("/api/policy-wording", operation_id="get_policy_wording")
def get_policy_wording() -> Text:
    """Get the policy wording, the contract that every decision follows."""
    with db.connect() as conn:
        row = conn.execute(
            "SELECT text FROM documents WHERE name = 'policy_wording'"
        ).fetchone()
    return Text(text=row["text"])


@app.get("/api/instructions", operation_id="get_instructions")
def get_instructions() -> Text:
    """Get the UnderCover Agent's instructions."""
    return Text(text=INSTRUCTIONS.read_text(encoding="utf-8"))


@app.get("/api/handlers", operation_id="list_handlers")
def list_handlers() -> list[Handler]:
    """List the claims handlers who can sign off a payout."""
    with db.connect() as conn:
        rows = conn.execute("SELECT data FROM handlers ORDER BY handler_id").fetchall()
    return [Handler.model_validate_json(row["data"]) for row in rows]


def state(conn: sqlite3.Connection, claim_id: str) -> ClaimState:
    return ClaimState.model_validate(claims.find(conn, claim_id))


@app.post("/api/claims/{claim_id}/start", operation_id="start_claim")
def start_claim(claim_id: str, request: StartRequest) -> ClaimState:
    """Start work on a waiting claim, under the thread id of the run working it."""
    with db.connect() as conn:
        claims.start(conn, claim_id, request.thread_id)
        return state(conn, claim_id)


@app.post("/api/claims/{claim_id}/steps", operation_id="add_step")
def add_step(claim_id: str, request: StepRequest) -> Step:
    """Record one step of a run on a claim."""
    with db.connect() as conn:
        return Step.model_validate(
            claims.add_step(
                conn, claim_id, request.thread_id, request.kind, request.text
            )
        )


@app.get("/api/claims/{claim_id}/steps", operation_id="list_steps")
def list_steps(claim_id: str) -> list[Step]:
    """List every step of every run on a claim, oldest first."""
    with db.connect() as conn:
        return [Step.model_validate(s) for s in claims.steps(conn, claim_id)]


@app.post("/api/claims/{claim_id}/decision", operation_id="record_decision")
def record_decision(claim_id: str, request: DecisionRequest) -> ClaimState:
    """Record the decision on a claim in progress: approve, decline or refer."""
    with db.connect() as conn:
        claims.decide(conn, claim_id, request)
        return state(conn, claim_id)


@app.post("/api/claims/{claim_id}/payment", operation_id="pay_claim")
def pay_claim(claim_id: str, request: PaymentRequest) -> ClaimState:
    """Pay an approved claim its payout; one over the limit waits for a sign-off."""
    with db.connect() as conn:
        claims.pay(conn, claim_id, request.amount)
        return state(conn, claim_id)


@app.post("/api/claims/{claim_id}/sign-off", operation_id="sign_off")
def sign_off(claim_id: str, request: SignOffRequest) -> ClaimState:
    """Sign off an approval over the limit as a handler, which pays it."""
    with db.connect() as conn:
        claims.sign_off(conn, claim_id, request.handler_id)
        return state(conn, claim_id)


@app.post("/api/claims/{claim_id}/release", operation_id="release_claim")
def release_claim(claim_id: str, request: ReleaseRequest) -> ClaimState:
    """Put a claim in progress back in the queue after its run failed."""
    with db.connect() as conn:
        claims.release(conn, claim_id, request.thread_id)
        return state(conn, claim_id)


@app.post("/api/claims/{claim_id}/run", operation_id="run_agent", status_code=202)
def run_agent(claim_id: str, background: BackgroundTasks) -> RunStarted:
    """Start the agent on a waiting claim in the background, under a new thread id."""
    with db.connect() as conn:
        claims.refuse_unless(claims.find(conn, claim_id), "waiting", "run")
    thread_id = str(uuid.uuid4())
    background.add_task(run, claim_id, thread_id)
    return RunStarted(claim_id=claim_id, thread_id=thread_id)
