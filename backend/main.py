"""The UnderCover backend."""

import json
import sqlite3
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException

from backend.db import DATA_DIR, connect, db_path, seed
from backend.models import (
    Claim,
    ClaimHistory,
    ClaimSummary,
    Handler,
    Instructions,
    Plan,
    Policy,
    PolicyWording,
)

INSTRUCTIONS = Path(__file__).parent / "instructions.md"


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


def load_claim(connection: sqlite3.Connection, claim_id: str) -> Claim:
    row = connection.execute(f"{CLAIMS} WHERE claim_id = ?", (claim_id,)).fetchone()
    return Claim.model_validate(claim_fields(find(row, f"claim {claim_id}")))


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
