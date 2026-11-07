import runpy
import sys

import pytest
from langchain_core.messages import ToolMessage

from agent import main
from agent.stub import StubModel


class BrokenModel(StubModel):
    """Fails once it has recorded a decision, before it pays."""

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        if any(
            isinstance(m, ToolMessage) and m.name == "record_decision" for m in messages
        ):
            raise RuntimeError("The model is down")
        return super()._generate(messages, stop, run_manager, **kwargs)


def test_run_agent_from_the_backend(backend, monkeypatch):
    monkeypatch.setenv("MODEL_NAME", "stub")
    response = backend.post("/api/claims/CLM-1001/run")
    assert response.status_code == 202
    claim = backend.get("/api/claims/CLM-1001").json()
    assert claim["thread_id"] == response.json()["thread_id"]
    assert claim["status"] == "decided"


def test_a_failed_run_goes_back_to_the_queue(backend):
    with pytest.raises(RuntimeError, match="The model is down"):
        main.run("CLM-1001", "thread-1", BrokenModel())
    claim = backend.get("/api/claims/CLM-1001").json()
    assert claim["status"] == "waiting"
    assert claim["decision"] is None
    steps = backend.get("/api/claims/CLM-1001/steps").json()
    assert "record_decision" in steps[-2]["text"]
    assert steps[-1] == steps[-1] | {
        "kind": "error",
        "text": "The agent stopped: The model is down",
    }
    assert main.run("CLM-1001", "thread-2", StubModel()).startswith("Approved")


def test_work_queue_decides_every_waiting_claim(backend, monkeypatch, capsys):
    monkeypatch.setenv("MODEL_NAME", "stub")
    backend.post("/api/claims/CLM-1001/start", json={"thread_id": "busy"})
    monkeypatch.setattr(sys, "argv", ["agent", "queue"])
    runpy.run_module("agent", run_name="__main__")
    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 24
    assert lines[0] == "CLM-1002: Approved, payout $1,150.00."
    statuses = {c["claim_id"]: c["status"] for c in backend.get("/api/claims").json()}
    assert statuses.pop("CLM-1001") == "in_progress"
    assert set(statuses.values()) == {"decided", "awaiting_signoff"}
    assert statuses["CLM-1002"] == "awaiting_signoff"
