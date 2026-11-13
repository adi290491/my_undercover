"""The claims queue and the rules for moving a claim through it."""

import json
import sqlite3
from typing import Any

from fastapi import HTTPException


def view(row: sqlite3.Row) -> dict[str, Any]:
    """Return a claim's record with where it stands."""
    return json.loads(row["data"]) | {"status": row["status"]}


def find(conn: sqlite3.Connection, claim_id: str) -> dict[str, Any]:
    """Return one claim, or raise 404."""
    row = conn.execute(
        "SELECT * FROM claims WHERE claim_id = ?", (claim_id,)
    ).fetchone()
    if row is None:
        raise HTTPException(404, f"There is no claim {claim_id}.")
    return view(row)


def queue(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Return every claim in the queue, in id order."""
    return [view(row) for row in conn.execute("SELECT * FROM claims ORDER BY claim_id")]
