"""The UnderCover database: SQLite, seeded from the records in data/."""

import json
import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

SCHEMA = """
CREATE TABLE company (id INTEGER PRIMARY KEY CHECK (id = 1), data TEXT NOT NULL);
CREATE TABLE plans (plan TEXT PRIMARY KEY, data TEXT NOT NULL);
CREATE TABLE policies (policy_id TEXT PRIMARY KEY, data TEXT NOT NULL);
CREATE TABLE customers (customer_id TEXT PRIMARY KEY, data TEXT NOT NULL);
CREATE TABLE handlers (handler_id TEXT PRIMARY KEY, data TEXT NOT NULL);
CREATE TABLE documents (name TEXT PRIMARY KEY, text TEXT NOT NULL);
CREATE TABLE claims (
    claim_id TEXT PRIMARY KEY,
    data TEXT NOT NULL,
    status TEXT NOT NULL,
    thread_id TEXT
);
CREATE TABLE decisions (
    claim_id TEXT PRIMARY KEY,
    decision TEXT NOT NULL,
    payout REAL NOT NULL,
    reason TEXT NOT NULL,
    policy_section INTEGER NOT NULL,
    decided_at TEXT NOT NULL
);
CREATE TABLE payments (
    claim_id TEXT PRIMARY KEY,
    amount REAL NOT NULL,
    paid_at TEXT NOT NULL
);
CREATE TABLE sign_offs (
    claim_id TEXT PRIMARY KEY,
    handler_id TEXT NOT NULL,
    handler_name TEXT NOT NULL,
    signed_at TEXT NOT NULL
);
CREATE TABLE steps (
    step_id INTEGER PRIMARY KEY AUTOINCREMENT,
    claim_id TEXT NOT NULL,
    thread_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    text TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def db_path() -> Path:
    """Return the database file: the one in UNDERCOVER_DB, or backend/undercover.db."""
    return Path(os.environ.get("UNDERCOVER_DB") or ROOT / "backend" / "undercover.db")


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    """Open the database for one unit of work, committed when it ends."""
    conn = sqlite3.connect(db_path(), timeout=30)
    conn.row_factory = sqlite3.Row
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def record(
    conn: sqlite3.Connection, table: str, key: str, value: str
) -> dict[str, Any] | None:
    """Return the record in a table whose key column has this value."""
    row = conn.execute(
        f"SELECT data FROM {table} WHERE {key} = ?",  # noqa: S608
        (value,),
    ).fetchone()
    return json.loads(row["data"]) if row else None


def load(name: str) -> Any:
    """Read one JSON file from data/."""
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def seed() -> int:
    """Build the database from scratch from data/, and return the number of claims."""
    db_path().unlink(missing_ok=True)
    plans = load("plans.json")
    customers = {c["customer_id"]: c for c in load("customers.json")}
    claims = load("claims.json")
    wording = (DATA / "policy_wording.md").read_text(encoding="utf-8")
    with connect() as conn:
        conn.executescript(SCHEMA)
        conn.execute(
            "INSERT INTO company VALUES (1, ?)", (json.dumps(load("company.json")),)
        )
        conn.executemany(
            "INSERT INTO plans VALUES (?, ?)",
            [
                (
                    p["plan"],
                    json.dumps(
                        p | {"deductible_applies_to": plans["deductible_applies_to"]}
                    ),
                )
                for p in plans["plans"]
            ],
        )
        conn.executemany(
            "INSERT INTO policies VALUES (?, ?)",
            [(p["policy_id"], json.dumps(p)) for p in load("policies.json")],
        )
        conn.executemany(
            "INSERT INTO customers VALUES (?, ?)",
            [(c["customer_id"], json.dumps(c)) for c in customers.values()],
        )
        conn.executemany(
            "INSERT INTO handlers VALUES (?, ?)",
            [(h["handler_id"], json.dumps(h)) for h in load("handlers.json")],
        )
        conn.execute("INSERT INTO documents VALUES ('policy_wording', ?)", (wording,))
        conn.executemany(
            "INSERT INTO claims VALUES (?, ?, 'waiting', NULL)",
            [
                (
                    c["claim_id"],
                    json.dumps(
                        c | {"customer_name": customers[c["customer_id"]]["name"]}
                    ),
                )
                for c in claims
            ],
        )
    return len(claims)


def ensure() -> None:
    """Seed the database if it doesn't exist yet."""
    if not db_path().exists():
        seed()
