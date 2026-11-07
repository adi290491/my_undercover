import runpy
import sys

from langchain_openai import ChatOpenAI

from agent import main
from agent.stub import StubModel

from .conftest import scripted

REASON = "Section 3 covers a crew problem. The receipts total $420.00."


def decision(payout: float) -> dict:
    return {
        "decision": "approve",
        "payout": payout,
        "reason": REASON,
        "policy_section": "Section 3, Trip Delay",
    }


def test_run_decides_a_claim(backend):
    llm = scripted(
        ("get_claim", {}),
        ("get_policy", {"policy_id": "POL-2001"}),
        ("get_policy_wording", {}),
        ("record_decision", decision(420.0)),
        ("pay_claim", {"amount": 420.0}),
        reply="Approved, $420.00.",
    )
    assert main.run("CLM-1001", "thread-1", llm) == "Approved, $420.00."
    claim = backend.get("/api/claims/CLM-1001").json()
    assert claim["status"] == "decided"
    assert claim["thread_id"] == "thread-1"
    assert claim["payment"]["amount"] == 420.0
    steps = backend.get("/api/claims/CLM-1001/steps").json()
    assert [s["kind"] for s in steps] == ["tool_call", "tool_result"] * 5 + ["message"]
    assert steps[0]["text"] == "get_claim({})"
    assert steps[3]["text"].startswith('get_policy: {"policy_id":"POL-2001"')


def test_payment_over_the_limit_is_refused(backend):
    llm = scripted(
        ("record_decision", decision(1500.0)),
        ("pay_claim", {"amount": 1500.0}),
    )
    main.run("CLM-1001", "thread-1", llm)
    claim = backend.get("/api/claims/CLM-1001").json()
    assert claim["status"] == "awaiting_signoff"
    assert claim["payment"] is None
    steps = backend.get("/api/claims/CLM-1001/steps").json()
    assert "waits for a handler's sign-off" in steps[3]["text"]


def test_the_agent_has_no_sign_off_tool():
    assert [t.name for t in main.tools_for("CLM-1001")] == [
        "get_claim",
        "get_policy",
        "get_plan",
        "get_claim_history",
        "get_policy_wording",
        "record_decision",
        "pay_claim",
    ]


def test_read_tools_reach_the_backend():
    tools = {t.name: t for t in main.tools_for("CLM-1001")}
    assert '"deductible":50.0' in tools["get_plan"].invoke({"plan": "premium"})
    history = tools["get_claim_history"].invoke({"customer_id": "CUS-3001"})
    assert "CLM-0412" in history


def test_system_prompt_comes_from_the_backend(backend, monkeypatch):
    prompts = []
    create_agent = main.create_agent

    def spy(*args, **kwargs):
        prompts.append(kwargs["system_prompt"])
        return create_agent(*args, **kwargs)

    monkeypatch.setattr(main, "create_agent", spy)
    main.run("CLM-1001", "thread-1", StubModel())
    assert prompts == [backend.get("/api/instructions").json()["instructions"]]


def test_stub_model_approves_in_full(backend):
    assert main.run("CLM-1001", "thread-1", StubModel()) == "Approved, payout $420.00."
    assert backend.get("/api/claims/CLM-1001").json()["status"] == "decided"


def test_model_name(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.delenv("MODEL_NAME", raising=False)
    default = main.model()
    assert isinstance(default, ChatOpenAI)
    assert default.model_name == "openai/gpt-6-luna"
    assert default.reasoning_effort == "low"
    monkeypatch.setenv("MODEL_NAME", "openrouter/free")
    free = main.model()
    assert isinstance(free, ChatOpenAI)
    assert free.model_name == "openrouter/free"
    monkeypatch.setenv("MODEL_NAME", "stub")
    assert isinstance(main.model(), StubModel)


def test_command_line(backend, monkeypatch, capsys):
    monkeypatch.setenv("MODEL_NAME", "stub")
    monkeypatch.setattr(sys, "argv", ["agent", "CLM-1001"])
    runpy.run_module("agent", run_name="__main__")
    assert capsys.readouterr().out == "Approved, payout $420.00.\n"
