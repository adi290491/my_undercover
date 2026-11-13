"""Many requests on the same claim at once: one wins and the others are refused."""

import threading
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from agent import main as agent
from backend.main import app

AT_ONCE = 10
ONE_WINS = [200] + [409] * (AT_ONCE - 1)
REASON = (
    "The flight was canceled for a crew problem. "
    "The hotel, meals and taxis are covered."
)
SMALL = {"CLM-1001": 420.0, "CLM-1004": 186.0, "CLM-1005": 243.0}
LARGE = {"CLM-1002": 1150.0, "CLM-1003": 3800.0}


def at_once(send):
    """Send AT_ONCE requests at the same moment, and return their status codes."""
    barrier = threading.Barrier(AT_ONCE)

    def go(i):
        client = TestClient(app)
        barrier.wait()
        return send(client, i).status_code

    with ThreadPoolExecutor(AT_ONCE) as pool:
        return list(pool.map(go, range(AT_ONCE)))


def start(client, claim_id):
    response = client.post(
        f"/api/claims/{claim_id}/start", json={"thread_id": "thread-1"}
    )
    assert response.status_code == 200, response.text


def decide(client, claim_id, payout):
    body = {
        "decision": "approve",
        "payout": payout,
        "reason": REASON,
        "policy_section": 3,
    }
    return client.post(f"/api/claims/{claim_id}/decision", json=body)


@pytest.mark.parametrize("claim_id", [*SMALL, *LARGE])
def test_only_one_run_can_start_a_claim(client, claim_id):
    thread_ids = [str(uuid.uuid4()) for _ in range(AT_ONCE)]
    codes = at_once(
        lambda c, i: c.post(
            f"/api/claims/{claim_id}/start", json={"thread_id": thread_ids[i]}
        )
    )
    assert sorted(codes) == ONE_WINS
    owner = client.get(f"/api/claims/{claim_id}").json()["thread_id"]
    assert owner == thread_ids[codes.index(200)]


@pytest.mark.parametrize(("claim_id", "payout"), SMALL.items())
def test_only_one_decision_is_recorded(client, claim_id, payout):
    start(client, claim_id)
    assert sorted(at_once(lambda c, _: decide(c, claim_id, payout))) == ONE_WINS


@pytest.mark.parametrize(("claim_id", "payout"), SMALL.items())
def test_a_claim_is_paid_once(client, claim_id, payout):
    start(client, claim_id)
    decide(client, claim_id, payout)
    codes = at_once(
        lambda c, _: c.post(f"/api/claims/{claim_id}/payment", json={"amount": payout})
    )
    assert sorted(codes) == ONE_WINS
    assert client.get(f"/api/claims/{claim_id}").json()["payment"]["amount"] == payout


@pytest.mark.parametrize(("claim_id", "payout"), LARGE.items())
def test_a_payout_is_signed_off_once(client, claim_id, payout):
    handlers = ["HND-01", "HND-02", "HND-03"]
    start(client, claim_id)
    decide(client, claim_id, payout)
    codes = at_once(
        lambda c, i: c.post(
            f"/api/claims/{claim_id}/sign-off", json={"handler_id": handlers[i % 3]}
        )
    )
    assert sorted(codes) == ONE_WINS
    claim = client.get(f"/api/claims/{claim_id}").json()
    assert claim["payment"]["amount"] == payout
    assert claim["sign_off"]["handler_id"] == handlers[codes.index(200) % 3]


def test_only_one_of_many_run_clicks_starts_a_run(client, monkeypatch):
    monkeypatch.setattr(agent, "backend", lambda: TestClient(app))
    monkeypatch.setenv("MODEL_NAME", "stub")
    codes = at_once(lambda c, _: c.post("/api/claims/CLM-1001/run"))
    assert sorted(codes) == [202] + [409] * (AT_ONCE - 1)
    claim = client.get("/api/claims/CLM-1001").json()
    assert claim["status"] == "decided"
    steps = client.get("/api/claims/CLM-1001/steps").json()
    assert {s["thread_id"] for s in steps} == {claim["thread_id"]}
    assert [s["kind"] for s in steps if s["kind"] == "error"] == []
