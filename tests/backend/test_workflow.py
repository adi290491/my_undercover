import json

import pytest

from backend import db

REASON = (
    "The flight was canceled for a crew problem. "
    "The hotel, meals and taxis are covered."
)


def start(client, claim_id="CLM-1001", thread_id="thread-1"):
    response = client.post(
        f"/api/claims/{claim_id}/start", json={"thread_id": thread_id}
    )
    assert response.status_code == 200, response.text
    return response.json()


def decide(client, claim_id="CLM-1001", decision="approve", payout=420.0, **changes):
    body = {
        "decision": decision,
        "payout": payout,
        "reason": REASON,
        "policy_section": 3,
    } | changes
    return client.post(f"/api/claims/{claim_id}/decision", json=body)


def pay(client, claim_id="CLM-1001", amount=420.0):
    return client.post(f"/api/claims/{claim_id}/payment", json={"amount": amount})


def sign_off(client, claim_id="CLM-1002", handler_id="HND-01"):
    return client.post(
        f"/api/claims/{claim_id}/sign-off", json={"handler_id": handler_id}
    )


def status(client, claim_id="CLM-1001"):
    return client.get(f"/api/claims/{claim_id}").json()["status"]


def test_start_claim(client):
    claim = start(client)
    assert claim["status"] == "in_progress"
    assert claim["thread_id"] == "thread-1"
    again = client.post("/api/claims/CLM-1001/start", json={"thread_id": "thread-2"})
    assert again.status_code == 409
    assert again.json()["detail"] == (
        "CLM-1001 is in progress, so it can't be started. "
        "Only a claim that is waiting can."
    )
    unknown = client.post("/api/claims/CLM-9999/start", json={"thread_id": "t"})
    assert unknown.status_code == 404


def test_steps(client):
    start(client)
    for kind, text in [("tool_call", "Read the claim"), ("tool_result", "{}")]:
        response = client.post(
            "/api/claims/CLM-1001/steps",
            json={"thread_id": "thread-1", "kind": kind, "text": text},
        )
        assert response.status_code == 200
    steps = client.get("/api/claims/CLM-1001/steps").json()
    assert [(s["kind"], s["text"], s["thread_id"]) for s in steps] == [
        ("tool_call", "Read the claim", "thread-1"),
        ("tool_result", "{}", "thread-1"),
    ]
    assert steps[0]["step_id"] < steps[1]["step_id"]
    assert steps[0]["created_at"]
    bad = client.post(
        "/api/claims/CLM-1001/steps",
        json={"thread_id": "thread-1", "kind": "thought", "text": "Hmm"},
    )
    assert bad.status_code == 422
    assert client.get("/api/claims/CLM-9999/steps").status_code == 404


def test_only_a_claim_in_progress_can_be_decided(client):
    response = decide(client)
    assert response.status_code == 409
    assert "CLM-1001 is waiting, so it can't be decided" in response.json()["detail"]


@pytest.mark.parametrize("decision", ["decline", "refer"])
def test_decline_or_refer_is_decided_at_once(client, decision):
    start(client)
    response = decide(client, decision=decision, payout=0)
    assert response.status_code == 200
    assert response.json()["status"] == "decided"
    assert response.json()["decision"]["decision"] == decision
    assert response.json()["payment"] is None


def test_payouts_must_fit_the_decision(client):
    start(client)
    declined = decide(client, decision="decline", payout=50)
    assert declined.status_code == 422
    assert declined.json()["detail"] == "A decline has a payout of 0."
    assert decide(client, decision="refer", payout=10).status_code == 422
    approved = decide(client, decision="approve", payout=0)
    assert approved.status_code == 422
    assert approved.json()["detail"] == "An approval needs a payout above $0.00."
    assert decide(client, decision="maybe").status_code == 422


def test_reason_is_two_or_three_sentences(client):
    start(client)
    one = decide(client, reason="Covered in full.")
    assert one.status_code == 422
    assert one.json()["detail"] == (
        "The reason must be two or three sentences. This one has 1."
    )
    four = decide(client, reason="One. Two. Three. Four.")
    assert four.status_code == 422
    assert decide(client, reason="").status_code == 422
    with_amounts = decide(client, reason="We pay $420.00 in full. Section 3 covers it.")
    assert with_amounts.status_code == 200


def test_section_must_be_in_the_wording(client):
    start(client)
    response = decide(client, policy_section=13)
    assert response.status_code == 422
    assert response.json()["detail"] == (
        "There is no section 13 in the policy wording. Its sections run from 1 to 12."
    )


def test_one_decision_per_run(client):
    start(client)
    assert decide(client).status_code == 200
    again = decide(client, payout=400)
    assert again.status_code == 409
    assert again.json()["detail"] == "CLM-1001 already has a decision."


def test_small_approval_is_decided_once_paid(client):
    start(client)
    approved = decide(client).json()
    assert approved["status"] == "in_progress"
    assert approved["decision"]["payout"] == 420.0
    wrong = pay(client, amount=400)
    assert wrong.status_code == 409
    assert (
        wrong.json()["detail"]
        == "The amount must match the approved payout of $420.00."
    )
    paid = pay(client)
    assert paid.status_code == 200
    assert paid.json()["status"] == "decided"
    assert paid.json()["payment"]["amount"] == 420.0
    again = pay(client)
    assert again.status_code == 409
    assert again.json()["detail"] == "CLM-1001 has already been paid."


def test_approval_of_exactly_the_limit_needs_no_sign_off(client):
    start(client, "CLM-1002")
    assert decide(client, "CLM-1002", payout=1000.0).json()["status"] == "in_progress"
    assert pay(client, "CLM-1002", 1000.0).json()["status"] == "decided"


def test_payment_over_the_limit_waits_for_sign_off(client):
    start(client, "CLM-1002")
    assert (
        decide(client, "CLM-1002", payout=1150.0).json()["status"] == "awaiting_signoff"
    )
    refused = pay(client, "CLM-1002", 1150.0)
    assert refused.status_code == 403
    assert refused.json()["detail"].startswith(
        "The payout of $1,150.00 is over the $1,000.00 limit, "
        "so a handler must sign it off"
    )
    claim = client.get("/api/claims/CLM-1002").json()
    assert claim["status"] == "awaiting_signoff"
    assert claim["payment"] is None


def test_the_limit_comes_from_the_company_settings(client):
    with db.connect() as conn:
        company = json.loads(conn.execute("SELECT data FROM company").fetchone()[0])
        company["payout_approval_limit"] = 500.0
        conn.execute("UPDATE company SET data = ?", (json.dumps(company),))
    start(client)
    assert decide(client, payout=420.0).json()["status"] == "in_progress"
    start(client, "CLM-1002")
    assert (
        decide(client, "CLM-1002", payout=600.0).json()["status"] == "awaiting_signoff"
    )


def test_sign_off_pays_the_claim(client):
    start(client, "CLM-1002")
    decide(client, "CLM-1002", payout=1150.0)
    signed = sign_off(client)
    assert signed.status_code == 200
    claim = signed.json()
    assert claim["status"] == "decided"
    assert claim["sign_off"]["handler_id"] == "HND-01"
    assert claim["sign_off"]["handler_name"] == "Dana Whitfield"
    assert claim["sign_off"]["signed_at"]
    assert claim["payment"]["amount"] == 1150.0
    assert pay(client, "CLM-1002", 1150.0).status_code == 409


def test_sign_off_refusals(client):
    start(client, "CLM-1002")
    assert sign_off(client).status_code == 409
    decide(client, "CLM-1002", payout=1150.0)
    unknown = sign_off(client, handler_id="HND-99")
    assert unknown.status_code == 404
    assert unknown.json()["detail"] == "There is no handler HND-99."
    with db.connect() as conn:
        conn.execute(
            "INSERT INTO handlers VALUES ('HND-04', ?)",
            (
                json.dumps(
                    {
                        "handler_id": "HND-04",
                        "name": "Sam Trainee",
                        "role": "Trainee",
                        "can_approve_over_limit": False,
                    }
                ),
            ),
        )
    refused = sign_off(client, handler_id="HND-04")
    assert refused.status_code == 403
    assert (
        refused.json()["detail"]
        == "Sam Trainee can't sign off a payout over the limit."
    )
    assert status(client, "CLM-1002") == "awaiting_signoff"


def test_no_approval_to_pay(client):
    start(client)
    assert pay(client).status_code == 409
    decide(client, decision="decline", payout=0)
    response = pay(client)
    assert response.status_code == 409
    assert response.json()["detail"] == "CLM-1001 has no approval to pay."


def test_release_puts_the_claim_back(client):
    start(client)
    decide(client)
    client.post(
        "/api/claims/CLM-1001/steps",
        json={"thread_id": "thread-1", "kind": "error", "text": "The run failed."},
    )
    other = client.post("/api/claims/CLM-1001/release", json={"thread_id": "thread-2"})
    assert other.status_code == 409
    assert other.json()["detail"] == (
        "CLM-1001 is being worked by another run, so this run can't release it."
    )
    released = client.post(
        "/api/claims/CLM-1001/release", json={"thread_id": "thread-1"}
    )
    assert released.status_code == 200
    claim = released.json()
    assert claim["status"] == "waiting"
    assert claim["decision"] is None
    assert claim["thread_id"] is None
    assert len(client.get("/api/claims/CLM-1001/steps").json()) == 1
    start(client, thread_id="thread-3")


def test_release_only_a_claim_in_progress(client):
    start(client, "CLM-1002")
    decide(client, "CLM-1002", payout=1150.0)
    response = client.post(
        "/api/claims/CLM-1002/release", json={"thread_id": "thread-1"}
    )
    assert response.status_code == 409
    assert status(client, "CLM-1002") == "awaiting_signoff"


def test_claim_shows_its_decision_with_the_section(client):
    start(client)
    decide(client)
    pay(client)
    claim = client.get("/api/claims/CLM-1001").json()
    section = claim["decision"]["policy_section"]
    assert section["number"] == 3
    assert section["title"] == "Trip Delay"
    assert section["text"].startswith("We pay when your carrier delays you")
    assert claim["decision"]["reason"] == REASON
    assert claim["payment"]["amount"] == 420.0
    summary = client.get("/api/claims").json()[0]
    assert (summary["decision"], summary["payout"]) == ("approve", 420.0)
