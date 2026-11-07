"""The UnderCover backend."""

import json
import sqlite3
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException

from backend.db import DATA_DIR, connect, db_path, seed
from backend.models import (
    Claim,
    ClaimHistory,
    ClaimSummary,
    Handler,
    Instructions,
    NewDecision,
    NewPayment,
    NewSignOff,
    NewStep,
    Plan,
    Policy,
    PolicyWording,
    Start,
    Status,
    Step,
)

INSTRUCTIONS = Path(__file__).parent / "instructions.md"
COMPANY = json.loads((DATA_DIR / "company.json").read_text(encoding="utf-8"))
APPROVAL_LIMIT: float = COMPANY["payout_approval_limit"]


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    if not db_path().exists():
        seed()
    yield


app = FastAPI(title="UnderCover", lifespan=lifespan)


def find(row: sqlite3.Row | None, what: str) -> sqlite3.Row:
    """Return the row, or raise a 404 naming what was missing."""
    if row is None:
        raise HTTPException(404, f"No {what}")
    return row


CLAIMS = (
    "SELECT claims.*, json_extract(customers.record, '$.name') AS customer_name "
    "FROM claims JOIN customers USING (customer_id)"
)


def claim_fields(row: sqlite3.Row) -> dict:
    """Merge a claim row's record with its status, thread and customer name."""
    return json.loads(row["record"]) | {
        "status": row["status"],
        "thread_id": row["thread_id"],
        "customer_name": row["customer_name"],
    }


def one(connection: sqlite3.Connection, sql: str, claim_id: str) -> dict | None:
    row = connection.execute(sql, (claim_id,)).fetchone()
    return dict(row) if row else None


def load_claim(connection: sqlite3.Connection, claim_id: str) -> Claim:
    row = connection.execute(f"{CLAIMS} WHERE claim_id = ?", (claim_id,)).fetchone()
    return Claim.model_validate(
        claim_fields(find(row, f"claim {claim_id}"))
        | {
            "decision": one(
                connection, "SELECT * FROM decisions WHERE claim_id = ?", claim_id
            ),
            "payment": one(
                connection, "SELECT * FROM payments WHERE claim_id = ?", claim_id
            ),
            "sign_off": one(
                connection,
                "SELECT handler_id, signed_at, "
                "json_extract(handlers.record, '$.name') AS handler_name "
                "FROM sign_offs JOIN handlers USING (handler_id) WHERE claim_id = ?",
                claim_id,
            ),
        }
    )


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def move(
    connection: sqlite3.Connection, claim_id: str, current: Status, new: Status
) -> None:
    """Move a claim from one status to another, or raise 409 if it isn't there."""
    moved = connection.execute(
        "UPDATE claims SET status = ? WHERE claim_id = ? AND status = ?",
        (new, claim_id, current),
    ).rowcount
    if not moved:
        status = load_claim(connection, claim_id).status
        raise HTTPException(409, f"Claim {claim_id} is {status}, not {current}")


def money(amount: float) -> str:
    return f"${amount:,.2f}"


@app.get("/api/health", operation_id="health")
def health() -> dict[str, str]:
    """Check that the backend is running."""
    return {"status": "ok"}


@app.get("/api/claims", operation_id="list_claims")
def list_claims() -> list[ClaimSummary]:
    """List every claim in the queue with where it stands."""
    with connect() as connection:
        rows = connection.execute(f"{CLAIMS} ORDER BY claim_id").fetchall()
    return [ClaimSummary.model_validate(claim_fields(row)) for row in rows]


@app.get("/api/claims/{claim_id}", operation_id="get_claim")
def get_claim(claim_id: str) -> Claim:
    """Get one claim in full: the story, the items and the documents."""
    with connect() as connection:
        return load_claim(connection, claim_id)


@app.get("/api/policies/{policy_id}", operation_id="get_policy")
def get_policy(policy_id: str) -> Policy:
    """Get a policy: its plan, add-ons, purchase date, trip and travelers."""
    with connect() as connection:
        row = connection.execute(
            "SELECT record FROM policies WHERE policy_id = ?", (policy_id,)
        ).fetchone()
    return Policy.model_validate_json(find(row, f"policy {policy_id}")["record"])


@app.get("/api/plans/{plan}", operation_id="get_plan")
def get_plan(plan: str) -> Plan:
    """Get a plan's limits, waiting periods and deductible."""
    with connect() as connection:
        row = connection.execute(
            "SELECT record FROM plans WHERE plan = ?", (plan,)
        ).fetchone()
    return Plan.model_validate_json(find(row, f"plan {plan}")["record"])


@app.get("/api/customers/{customer_id}/claims", operation_id="get_claim_history")
def get_claim_history(customer_id: str) -> ClaimHistory:
    """Get a customer's earlier claims, without their contact details."""
    with connect() as connection:
        row = connection.execute(
            "SELECT record FROM customers WHERE customer_id = ?", (customer_id,)
        ).fetchone()
    return ClaimHistory.model_validate_json(
        find(row, f"customer {customer_id}")["record"]
    )


@app.get("/api/policy-wording", operation_id="get_policy_wording")
def get_policy_wording() -> PolicyWording:
    """Get the policy wording, the contract that decisions follow."""
    text = (DATA_DIR / "policy_wording.md").read_text(encoding="utf-8")
    return PolicyWording(policy_wording=text)


@app.get("/api/instructions", operation_id="get_instructions")
def get_instructions() -> Instructions:
    """Get the UnderCover Agent's instructions."""
    return Instructions(instructions=INSTRUCTIONS.read_text(encoding="utf-8"))


@app.get("/api/handlers", operation_id="list_handlers")
def list_handlers() -> list[Handler]:
    """List the claims handlers."""
    with connect() as connection:
        rows = connection.execute("SELECT record FROM handlers ORDER BY 1").fetchall()
    return [Handler.model_validate_json(row["record"]) for row in rows]


@app.post("/api/claims/{claim_id}/start", operation_id="start_claim")
def start_claim(claim_id: str, start: Start) -> Claim:
    """Mark a waiting claim as in progress on an agent thread."""
    with connect() as connection:
        move(connection, claim_id, "waiting", "in_progress")
        connection.execute(
            "UPDATE claims SET thread_id = ? WHERE claim_id = ?",
            (start.thread_id, claim_id),
        )
        return load_claim(connection, claim_id)


@app.post("/api/claims/{claim_id}/steps", operation_id="add_step")
def add_step(claim_id: str, step: NewStep) -> Step:
    """Record one step the agent took on a claim."""
    with connect() as connection:
        load_claim(connection, claim_id)
        step_id = connection.execute(
            "INSERT INTO steps (claim_id, at, kind, text) VALUES (?, ?, ?, ?)",
            (claim_id, now(), step.kind, step.text),
        ).lastrowid
        row = connection.execute(
            "SELECT * FROM steps WHERE step_id = ?", (step_id,)
        ).fetchone()
    return Step.model_validate(dict(row))


@app.get("/api/claims/{claim_id}/steps", operation_id="list_steps")
def list_steps(claim_id: str) -> list[Step]:
    """List the steps the agent took on a claim, oldest first."""
    with connect() as connection:
        load_claim(connection, claim_id)
        rows = connection.execute(
            "SELECT * FROM steps WHERE claim_id = ? ORDER BY step_id", (claim_id,)
        ).fetchall()
    return [Step.model_validate(dict(row)) for row in rows]


@app.post("/api/claims/{claim_id}/decision", operation_id="record_decision")
def record_decision(claim_id: str, decision: NewDecision) -> Claim:
    """Record the decision on a claim in progress, with its payout and reason."""
    if decision.decision != "approve":
        new: Status = "decided"
    elif decision.payout > APPROVAL_LIMIT:
        new = "awaiting_signoff"
    else:
        new = "in_progress"
    with connect() as connection:
        move(connection, claim_id, "in_progress", new)
        if one(connection, "SELECT 1 FROM decisions WHERE claim_id = ?", claim_id):
            raise HTTPException(409, f"Claim {claim_id} already has a decision")
        connection.execute(
            "INSERT INTO decisions VALUES (?, ?, ?, ?, ?, ?)",
            (
                claim_id,
                decision.decision,
                round(decision.payout, 2),
                decision.reason,
                decision.policy_section,
                now(),
            ),
        )
        return load_claim(connection, claim_id)


@app.post("/api/claims/{claim_id}/payment", operation_id="pay_claim")
def pay_claim(claim_id: str, payment: NewPayment) -> Claim:
    """Pay an approved claim its payout; over the limit it needs a sign-off."""
    with connect() as connection:
        claim = load_claim(connection, claim_id)
        if claim.decision is None or claim.decision.decision != "approve":
            raise HTTPException(409, f"Claim {claim_id} has no approval to pay")
        payout = claim.decision.payout
        if payout > APPROVAL_LIMIT and claim.sign_off is None:
            raise HTTPException(
                403,
                f"A payout over {money(APPROVAL_LIMIT)} waits for a handler's sign-off",
            )
        if round(payment.amount, 2) != payout:
            raise HTTPException(
                409, f"The payment must be the approved payout of {money(payout)}"
            )
        move(connection, claim_id, "in_progress", "decided")
        connection.execute(
            "INSERT INTO payments VALUES (?, ?, ?)", (claim_id, payout, now())
        )
        return load_claim(connection, claim_id)


@app.post("/api/claims/{claim_id}/sign-off", operation_id="sign_off")
def sign_off(claim_id: str, sign_off: NewSignOff) -> Claim:
    """Sign off a payout over the limit as a handler, which pays it."""
    with connect() as connection:
        row = connection.execute(
            "SELECT record FROM handlers WHERE handler_id = ?", (sign_off.handler_id,)
        ).fetchone()
        handler = Handler.model_validate_json(
            find(row, f"handler {sign_off.handler_id}")["record"]
        )
        if not handler.can_approve_over_limit:
            raise HTTPException(403, f"{handler.name} cannot sign off this payout")
        move(connection, claim_id, "awaiting_signoff", "decided")
        connection.execute(
            "INSERT INTO sign_offs VALUES (?, ?, ?)",
            (claim_id, handler.handler_id, now()),
        )
        connection.execute(
            "INSERT INTO payments SELECT claim_id, payout, ? FROM decisions "
            "WHERE claim_id = ?",
            (now(), claim_id),
        )
        return load_claim(connection, claim_id)
