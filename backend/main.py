"""The UnderCover backend."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException

from backend import claims, db
from backend.models import (
    Claim,
    ClaimSummary,
    Handler,
    PastClaim,
    Plan,
    Policy,
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
