import json

import pytest

from backend.db import connect

REASON = "Section 3 covers a canceled flight. The receipts total $420.00."


def start(client, claim_id="CLM-1001"):
    return client.post(f"/api/claims/{claim_id}/start", json={"thread_id": "t-1"})


def decide(client, decision="approve", payout=420.0, claim_id="CLM-1001"):
    return client.post(
        f"/api/claims/{claim_id}/decision",
        json={
            "decision": decision,
            "payout": payout,
            "reason": REASON,
            "policy_section": "Section 3, Trip Delay",
        },
    )


def pay(client, amount, claim_id="CLM-1001"):
    return client.post(f"/api/claims/{claim_id}/payment", json={"amount": amount})


def sign(client, handler_id="HND-01", claim_id="CLM-1001"):
    return client.post(
        f"/api/claims/{claim_id}/sign-off", json={"handler_id": handler_id}
    )


def test_start_claim(client):
    claim = start(client).json()
    assert claim["status"] == "in_progress"
    assert claim["thread_id"] == "t-1"


def test_start_claim_twice_conflicts(client):
    start(client)
    response = start(client)
    assert response.status_code == 409
    assert response.json()["detail"] == "Claim CLM-1001 is in_progress, not waiting"


def test_start_unknown_claim(client):
    assert start(client, "CLM-9999").status_code == 404


def test_steps_are_listed_in_order(client):
    for kind, text in [("tool_call", "get_claim()"), ("tool_result", "{...}")]:
        step = client.post(
            "/api/claims/CLM-1001/steps", json={"kind": kind, "text": text}
        )
        assert step.json()["kind"] == kind
        assert step.json()["at"]
    steps = client.get("/api/claims/CLM-1001/steps").json()
    assert [s["text"] for s in steps] == ["get_claim()", "{...}"]


def test_steps_on_unknown_claim(client):
    assert client.get("/api/claims/CLM-9999/steps").status_code == 404


@pytest.mark.parametrize("decision", ["decline", "refer"])
def test_decline_or_refer_decides_the_claim(client, decision):
    start(client)
    claim = decide(client, decision, 0).json()
    assert claim["status"] == "decided"
    assert claim["decision"]["decision"] == decision
    assert claim["payment"] is None


@pytest.mark.parametrize(
    ("decision", "payout", "reason"),
    [
        ("decline", 100.0, REASON),
        ("refer", 50.0, REASON),
        ("approve", 0, REASON),
        ("approve", 420.0, "One. Two. Three. Four."),
        ("approve", -5.0, REASON),
    ],
)
def test_invalid_decisions_are_rejected(client, decision, payout, reason):
    start(client)
    response = client.post(
        "/api/claims/CLM-1001/decision",
        json={
            "decision": decision,
            "payout": payout,
            "reason": reason,
            "policy_section": "Section 3",
        },
    )
    assert response.status_code == 422


def test_decision_needs_a_claim_in_progress(client):
    assert decide(client).status_code == 409


def test_decision_cannot_be_recorded_twice(client):
    start(client)
    decide(client)
    response = decide(client)
    assert response.status_code == 409
    assert response.json()["detail"] == "Claim CLM-1001 already has a decision"


def test_approval_within_limit_is_paid(client):
    start(client)
    assert decide(client).json()["status"] == "in_progress"
    claim = pay(client, 420.0).json()
    assert claim["status"] == "decided"
    assert claim["payment"]["amount"] == 420.0


def test_payment_must_match_the_payout(client):
    start(client)
    decide(client)
    response = pay(client, 400.0)
    assert response.status_code == 409
    assert response.json()["detail"] == (
        "The payment must be the approved payout of $420.00"
    )


def test_payment_needs_an_approval(client):
    start(client)
    decide(client, "decline", 0)
    assert pay(client, 420.0).status_code == 409


def test_claim_cannot_be_paid_twice(client):
    start(client)
    decide(client)
    pay(client, 420.0)
    assert pay(client, 420.0).status_code == 409


def test_payout_over_the_limit_waits_for_sign_off(client):
    start(client)
    assert decide(client, payout=1500.0).json()["status"] == "awaiting_signoff"
    response = pay(client, 1500.0)
    assert response.status_code == 403
    assert response.json()["detail"] == (
        "A payout over $1,000.00 waits for a handler's sign-off"
    )
    claim = client.get("/api/claims/CLM-1001").json()
    assert claim["payment"] is None
    assert claim["status"] == "awaiting_signoff"


def test_sign_off_pays_the_claim(client):
    start(client)
    decide(client, payout=1500.0)
    claim = sign(client).json()
    assert claim["status"] == "decided"
    assert claim["payment"]["amount"] == 1500.0
    assert claim["sign_off"]["handler_name"] == "Dana Whitfield"
    assert pay(client, 1500.0).status_code == 409


def test_sign_off_needs_a_claim_awaiting_it(client):
    start(client)
    decide(client)
    assert sign(client).status_code == 409


def test_sign_off_by_unknown_handler(client):
    start(client)
    decide(client, payout=1500.0)
    assert sign(client, "HND-99").status_code == 404


def test_sign_off_by_handler_without_authority(client):
    with connect() as connection:
        connection.execute(
            "UPDATE handlers SET record = ? WHERE handler_id = 'HND-03'",
            (
                json.dumps(
                    {
                        "handler_id": "HND-03",
                        "name": "Priya Raman",
                        "role": "Claims Handler",
                        "can_approve_over_limit": False,
                    }
                ),
            ),
        )
    start(client)
    decide(client, payout=1500.0)
    assert sign(client, "HND-03").status_code == 403


def test_release_puts_a_claim_back_in_the_queue(client):
    start(client)
    decide(client)
    claim = client.post("/api/claims/CLM-1001/release").json()
    assert claim["status"] == "waiting"
    assert claim["decision"] is None


def test_release_leaves_a_decided_claim_alone(client):
    start(client)
    decide(client, "decline", 0)
    assert client.post("/api/claims/CLM-1001/release").status_code == 409


def test_run_agent_needs_a_waiting_claim(client):
    start(client)
    assert client.post("/api/claims/CLM-1001/run").status_code == 409
