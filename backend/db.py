"""The UnderCover database: SQLite, seeded from data/."""

import json
import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
DEFAULT_DB = Path(__file__).parent / "undercover.db"

SCHEMA = """
CREATE TABLE claims (
    claim_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    status TEXT NOT NULL,
    thread_id TEXT,
    record TEXT NOT NULL
);
CREATE TABLE policies (policy_id TEXT PRIMARY KEY, record TEXT NOT NULL);
CREATE TABLE customers (customer_id TEXT PRIMARY KEY, record TEXT NOT NULL);
CREATE TABLE plans (plan TEXT PRIMARY KEY, record TEXT NOT NULL);
CREATE TABLE handlers (handler_id TEXT PRIMARY KEY, record TEXT NOT NULL);
CREATE TABLE decisions (
    claim_id TEXT PRIMARY KEY,
    decision TEXT NOT NULL,
    payout REAL NOT NULL,
    reason TEXT NOT NULL,
    policy_section TEXT NOT NULL,
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
    signed_at TEXT NOT NULL
);
CREATE TABLE steps (
    step_id INTEGER PRIMARY KEY AUTOINCREMENT,
    claim_id TEXT NOT NULL,
    at TEXT NOT NULL,
    kind TEXT NOT NULL,
    text TEXT NOT NULL
);
"""


def db_path() -> Path:
    """Return the database file, from UNDERCOVER_DB or the default."""
    return Path(os.getenv("UNDERCOVER_DB", str(DEFAULT_DB)))


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    """Open the database in a transaction that commits on success."""
    connection = sqlite3.connect(db_path())
    connection.row_factory = sqlite3.Row
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def load(name: str) -> list[dict]:
    """Read one of the seed files in data/."""
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


def seed() -> None:
    """Rebuild the database from data/, with every claim waiting."""
    db_path().unlink(missing_ok=True)
    plans = json.loads((DATA_DIR / "plans.json").read_text(encoding="utf-8"))
    with connect() as connection:
        connection.executescript(SCHEMA)
        connection.executemany(
            "INSERT INTO claims (claim_id, customer_id, status, record) "
            "VALUES (?, ?, 'waiting', ?)",
            [
                (claim["claim_id"], claim["customer_id"], json.dumps(claim))
                for claim in load("claims.json")
            ],
        )
        connection.executemany(
            "INSERT INTO policies VALUES (?, ?)",
            [(p["policy_id"], json.dumps(p)) for p in load("policies.json")],
        )
        connection.executemany(
            "INSERT INTO customers VALUES (?, ?)",
            [(c["customer_id"], json.dumps(c)) for c in load("customers.json")],
        )
        connection.executemany(
            "INSERT INTO plans VALUES (?, ?)",
            [
                (
                    plan["plan"],
                    json.dumps(
                        plan | {"deductible_applies_to": plans["deductible_applies_to"]}
                    ),
                )
                for plan in plans["plans"]
            ],
        )
        connection.executemany(
            "INSERT INTO handlers VALUES (?, ?)",
            [(h["handler_id"], json.dumps(h)) for h in load("handlers.json")],
        )
