"""The claims queue and the rules for moving a claim through it."""

import json
import re
import sqlite3
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException

from backend import db
from backend.models import DecisionRequest

STATUS_WORDS = {
    "waiting": "waiting",
    "in_progress": "in progress",
    "awaiting_signoff": "awaiting sign-off",
    "decided": "decided",
}
SECTION = re.compile(r"^## (\d+)\. (.+)$", re.MULTILINE)


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def dollars(amount: float) -> str:
    return f"${amount:,.2f}"


def approval_limit(conn: sqlite3.Connection) -> float:
    """Return the payout over which a handler must sign off, from data/company.json."""
    company = conn.execute("SELECT data FROM company").fetchone()
    return json.loads(company["data"])["payout_approval_limit"]


def sections(conn: sqlite3.Connection) -> dict[int, dict[str, Any]]:
    """Return the policy wording's numbered sections, each with its title and text."""
    wording = conn.execute(
        "SELECT text FROM documents WHERE name = 'policy_wording'"
    ).fetchone()["text"]
    headings = list(SECTION.finditer(wording))
    result = {}
    for heading, following in zip(headings, [*headings[1:], None], strict=True):
        end = following.start() if following else len(wording)
        number = int(heading[1])
        result[number] = {
            "number": number,
            "title": heading[2].strip(),
            "text": wording[heading.end() : end].strip(),
        }
    return result


def sentences(text: str) -> int:
    """Count the sentences in a piece of text."""
    return len([s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s])


def one(conn: sqlite3.Connection, table: str, claim_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        f"SELECT * FROM {table} WHERE claim_id = ?",  # noqa: S608
        (claim_id,),
    ).fetchone()
    return dict(row) if row else None


def decision_of(conn: sqlite3.Connection, claim_id: str) -> dict[str, Any] | None:
    decision = one(conn, "decisions", claim_id)
    if decision is None:
        return None
    return decision | {"policy_section": sections(conn)[decision["policy_section"]]}


def view(conn: sqlite3.Connection, row: sqlite3.Row) -> dict[str, Any]:
    """Return a claim's record with its status, decision, payment and sign-off."""
    claim_id = row["claim_id"]
    return json.loads(row["data"]) | {
        "status": row["status"],
        "thread_id": row["thread_id"],
        "decision": decision_of(conn, claim_id),
        "payment": one(conn, "payments", claim_id),
        "sign_off": one(conn, "sign_offs", claim_id),
    }


def find(conn: sqlite3.Connection, claim_id: str) -> dict[str, Any]:
    """Return one claim, or raise 404."""
    row = conn.execute(
        "SELECT * FROM claims WHERE claim_id = ?", (claim_id,)
    ).fetchone()
    if row is None:
        raise HTTPException(404, f"There is no claim {claim_id}.")
    return view(conn, row)


def queue(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Return every claim in the queue in id order, with its decision and payout."""
    rows = conn.execute("SELECT * FROM claims ORDER BY claim_id").fetchall()
    summaries = []
    for row in rows:
        claim = view(conn, row)
        decision = claim["decision"] or {}
        summaries.append(
            claim
            | {"decision": decision.get("decision"), "payout": decision.get("payout")}
        )
    return summaries


def set_status(conn: sqlite3.Connection, claim_id: str, status: str) -> None:
    conn.execute("UPDATE claims SET status = ? WHERE claim_id = ?", (status, claim_id))


def refuse_unless(claim: dict[str, Any], status: str, action: str) -> None:
    """Raise 409 unless the claim is in the status the action needs."""
    if claim["status"] != status:
        raise HTTPException(
            409,
            f"{claim['claim_id']} is {STATUS_WORDS[claim['status']]}, so it can't be "
            f"{action}. Only a claim that is {STATUS_WORDS[status]} can.",
        )


def start(conn: sqlite3.Connection, claim_id: str, thread_id: str) -> None:
    """Move a waiting claim to in progress, under a run's thread id.

    Starting it again under the same thread id changes nothing, so a run that
    run_agent has already started can start its claim as usual."""
    claim = find(conn, claim_id)
    if claim["status"] == "in_progress" and claim["thread_id"] == thread_id:
        return
    refuse_unless(claim, "waiting", "started")
    conn.execute(
        "UPDATE claims SET status = 'in_progress', thread_id = ? WHERE claim_id = ?",
        (thread_id, claim_id),
    )


def add_step(
    conn: sqlite3.Connection, claim_id: str, thread_id: str, kind: str, text: str
) -> dict[str, Any]:
    """Record one step of a run on a claim."""
    find(conn, claim_id)
    cursor = conn.execute(
        "INSERT INTO steps (claim_id, thread_id, kind, text, created_at) "
        "VALUES (?, ?, ?, ?, ?) RETURNING *",
        (claim_id, thread_id, kind, text, now()),
    )
    return dict(cursor.fetchone())


def steps(conn: sqlite3.Connection, claim_id: str) -> list[dict[str, Any]]:
    """Return a claim's steps, oldest first."""
    find(conn, claim_id)
    rows = conn.execute(
        "SELECT * FROM steps WHERE claim_id = ? ORDER BY step_id", (claim_id,)
    )
    return [dict(row) for row in rows]


def check_decision(
    conn: sqlite3.Connection, decision: str, payout: float, reason: str, section: int
) -> None:
    """Raise 422 if a decision breaks the rules for decisions."""
    if decision == "approve" and payout <= 0:
        raise HTTPException(422, "An approval needs a payout above $0.00.")
    if decision != "approve" and payout != 0:
        raise HTTPException(422, f"A {decision} has a payout of 0.")
    count = sentences(reason)
    if count not in (2, 3):
        raise HTTPException(
            422, f"The reason must be two or three sentences. This one has {count}."
        )
    numbers = sections(conn)
    if section not in numbers:
        raise HTTPException(
            422,
            f"There is no section {section} in the policy wording. "
            f"Its sections run from {min(numbers)} to {max(numbers)}.",
        )


def decide(conn: sqlite3.Connection, claim_id: str, request: DecisionRequest) -> None:
    """Record the decision on a claim in progress, and move it on."""
    claim = find(conn, claim_id)
    refuse_unless(claim, "in_progress", "decided")
    if claim["decision"]:
        raise HTTPException(409, f"{claim_id} already has a decision.")
    decision, payout = request.decision, round(request.payout, 2)
    check_decision(conn, decision, payout, request.reason, request.policy_section)
    conn.execute(
        "INSERT INTO decisions VALUES (?, ?, ?, ?, ?, ?)",
        (
            claim_id,
            decision,
            payout,
            request.reason.strip(),
            request.policy_section,
            now(),
        ),
    )
    if decision != "approve":
        set_status(conn, claim_id, "decided")
    elif payout > approval_limit(conn):
        set_status(conn, claim_id, "awaiting_signoff")


def pay(conn: sqlite3.Connection, claim_id: str, amount: float) -> None:
    """Pay an approved claim, refusing a payout over the limit until signed off."""
    claim = find(conn, claim_id)
    decision = claim["decision"]
    if not decision or decision["decision"] != "approve":
        raise HTTPException(409, f"{claim_id} has no approval to pay.")
    if claim["payment"]:
        raise HTTPException(409, f"{claim_id} has already been paid.")
    limit = approval_limit(conn)
    if decision["payout"] > limit and not claim["sign_off"]:
        raise HTTPException(
            403,
            f"The payout of {dollars(decision['payout'])} is over the "
            f"{dollars(limit)} limit, so a handler must sign it off before it is "
            "paid. The claim is waiting for that sign-off, and the payment will be "
            "made then.",
        )
    if round(amount, 2) != decision["payout"]:
        raise HTTPException(
            409,
            f"The amount must match the approved payout of "
            f"{dollars(decision['payout'])}.",
        )
    conn.execute(
        "INSERT INTO payments VALUES (?, ?, ?)", (claim_id, decision["payout"], now())
    )
    set_status(conn, claim_id, "decided")


def sign_off(conn: sqlite3.Connection, claim_id: str, handler_id: str) -> None:
    """Sign off an approval over the limit as a handler, and pay it."""
    claim = find(conn, claim_id)
    handler = db.record(conn, "handlers", "handler_id", handler_id)
    if handler is None:
        raise HTTPException(404, f"There is no handler {handler_id}.")
    refuse_unless(claim, "awaiting_signoff", "signed off")
    if not handler["can_approve_over_limit"]:
        raise HTTPException(
            403, f"{handler['name']} can't sign off a payout over the limit."
        )
    signed_at = now()
    conn.execute(
        "INSERT INTO sign_offs VALUES (?, ?, ?, ?)",
        (claim_id, handler_id, handler["name"], signed_at),
    )
    conn.execute(
        "INSERT INTO payments VALUES (?, ?, ?)",
        (claim_id, claim["decision"]["payout"], signed_at),
    )
    set_status(conn, claim_id, "decided")


def release(conn: sqlite3.Connection, claim_id: str, thread_id: str) -> None:
    """Put a claim in progress back in the queue, dropping its unpaid decision."""
    claim = find(conn, claim_id)
    refuse_unless(claim, "in_progress", "released")
    if claim["thread_id"] != thread_id:
        raise HTTPException(
            409,
            f"{claim_id} is being worked by another run, so this run can't release it.",
        )
    conn.execute("DELETE FROM decisions WHERE claim_id = ?", (claim_id,))
    conn.execute(
        "UPDATE claims SET status = 'waiting', thread_id = NULL WHERE claim_id = ?",
        (claim_id,),
    )
