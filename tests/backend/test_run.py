import pytest
from fastapi.testclient import TestClient

from agent import main as agent
from agent.__main__ import main as cli
from agent.stub import StubModel
from backend.main import app


@pytest.fixture(autouse=True)
def stub_agent(monkeypatch):
    """Run the agent on the stub model, against the backend in this process."""
    monkeypatch.setattr(agent, "backend", lambda: TestClient(app))
    monkeypatch.setenv("MODEL_NAME", "stub")


def test_run_agent_works_the_claim_in_the_background(client):
    response = client.post("/api/claims/CLM-1001/run")
    assert response.status_code == 202
    started = response.json()
    assert started["claim_id"] == "CLM-1001"
    claim = client.get("/api/claims/CLM-1001").json()
    assert claim["status"] == "decided"
    assert claim["thread_id"] == started["thread_id"]
    steps = client.get("/api/claims/CLM-1001/steps").json()
    assert len(steps) == 15
    assert {s["thread_id"] for s in steps} == {started["thread_id"]}


def test_run_agent_only_on_a_waiting_claim(client):
    client.post("/api/claims/CLM-1001/start", json={"thread_id": "by-hand"})
    response = client.post("/api/claims/CLM-1001/run")
    assert response.status_code == 409
    assert response.json()["detail"] == (
        "CLM-1001 is in progress, so it can't be run. Only a claim that is waiting can."
    )
    assert client.post("/api/claims/CLM-9999/run").status_code == 404


def test_the_queue_command_works_every_waiting_claim(client):
    client.post("/api/claims/CLM-1003/start", json={"thread_id": "by-hand"})
    lines = list(agent.work_queue(StubModel()))
    assert len(lines) == 24
    assert lines[0].startswith("CLM-1001: approve, $420.00, now decided")
    claims = {c["claim_id"]: c for c in client.get("/api/claims").json()}
    for claim_id, claim in claims.items():
        if claim_id == "CLM-1003":
            assert claim["status"] == "in_progress"
        elif claim["amount_claimed"] > 1000:
            assert claim["status"] == "awaiting_signoff", claim_id
        else:
            assert claim["status"] == "decided", claim_id
    assert client.get("/api/claims/CLM-1003").json()["thread_id"] == "by-hand"


def test_the_queue_skips_a_claim_another_run_took(monkeypatch):
    def run(claim_id, thread_id, llm=None):
        if claim_id == "CLM-1001":
            raise agent.Refused("Refused (409): CLM-1001 is in progress.")
        return f"{claim_id}: done"

    monkeypatch.setattr(agent, "run", run)
    lines = list(agent.work_queue())
    assert lines[0] == "CLM-1001: skipped. Refused (409): CLM-1001 is in progress."
    assert lines[1] == "CLM-1002: done"


def test_the_queue_from_the_command_line(monkeypatch, capsys):
    monkeypatch.setattr(agent, "run", lambda claim_id, thread_id, llm=None: claim_id)
    assert cli(["queue"]) == 0
    out = capsys.readouterr().out.split()
    assert out[0] == "CLM-1001"
    assert len(out) == 25
