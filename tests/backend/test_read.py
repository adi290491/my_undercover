import runpy
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from backend import db
from backend.main import app

_recording: list[list[str]] = []


def _record_opens(event: str, args: tuple) -> None:
    if event == "open" and _recording:
        _recording[-1].append(str(args[0]))


sys.addaudithook(_record_opens)


def test_seed_reads_only_the_queue_records():
    opened: list[str] = []
    _recording.append(opened)
    try:
        db.seed()
    finally:
        _recording.pop()
    paths = [Path(p).resolve() for p in opened]
    read = {
        p.relative_to(db.DATA).as_posix() for p in paths if p.is_relative_to(db.DATA)
    }
    assert read == {
        "company.json",
        "plans.json",
        "policies.json",
        "customers.json",
        "handlers.json",
        "claims.json",
        "policy_wording.md",
    }
    assert not any("evals" in p or "security" in p for p in read)


def test_seed_command(capsys):
    runpy.run_module("backend.seed", run_name="__main__")
    assert "with 25 claims, all waiting" in capsys.readouterr().out


def test_startup_seeds_a_missing_database(tmp_path, monkeypatch):
    monkeypatch.setenv("UNDERCOVER_DB", str(tmp_path / "new.db"))
    with TestClient(app) as client:
        assert len(client.get("/api/claims").json()) == 25
    assert (tmp_path / "new.db").exists()


def test_startup_keeps_an_existing_database(client):
    with db.connect() as conn:
        conn.execute("UPDATE claims SET status = 'decided' WHERE claim_id = 'CLM-1001'")
    with TestClient(app) as started:
        assert started.get("/api/claims/CLM-1001").json()["status"] == "decided"


def test_list_claims(client):
    claims = client.get("/api/claims").json()
    assert len(claims) == 25
    assert {c["status"] for c in claims} == {"waiting"}
    assert claims[0] == {
        "claim_id": "CLM-1001",
        "claim_type": "trip_delay",
        "customer_name": "Maya Patel",
        "amount_claimed": 420.0,
        "submitted_on": "2026-06-24",
        "status": "waiting",
    }


def test_get_claim(client):
    claim = client.get("/api/claims/CLM-1001").json()
    assert claim["story"].startswith("My flight home from Rome")
    assert [i["amount"] for i in claim["items"]] == [245.0, 95.0, 80.0]
    assert len(claim["documents"]) == 4
    assert claim["amount_claimed"] == 420.0
    assert claim["policy_id"] == "POL-2001"
    assert claim["status"] == "waiting"


def test_unknown_claim(client):
    response = client.get("/api/claims/CLM-9999")
    assert response.status_code == 404
    assert response.json()["detail"] == "There is no claim CLM-9999."
