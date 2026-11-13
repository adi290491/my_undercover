import ast
import importlib
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatResult
from langchain_openai import ChatOpenAI

import backend.main as backend_main
from agent import main
from agent.__main__ import main as cli
from agent.stub import REASON, StubModel, tool_call
from backend.main import app

AGENT = Path(main.__file__).parent


@pytest.fixture(autouse=True)
def in_process_backend(monkeypatch):
    """Send the agent's requests to the backend in this process."""
    monkeypatch.setattr(main, "backend", lambda: TestClient(app))


class Scripted(GenericFakeChatModel):
    """A model that gives a fixed list of replies."""

    def bind_tools(self, tools: Any, **kwargs: Any) -> "Scripted":
        return self


def scripted(*replies: AIMessage) -> Scripted:
    return Scripted(messages=iter(replies))


class Broken(StubModel):
    """A model that works for a few calls and then fails."""

    calls: int = 0
    fail_on: int = 1

    def _generate(
        self, messages: list[BaseMessage], stop=None, run_manager=None, **kwargs
    ) -> ChatResult:
        self.calls += 1
        if self.calls >= self.fail_on:
            raise RuntimeError("The model is down.")
        return super()._generate(messages, stop, run_manager, **kwargs)


WRITES = ("record_decision", "pay_claim")


class Twice(StubModel):
    """The stub model, asking for each write twice in one turn, as real models can."""

    def next_step(self, messages: list[BaseMessage]) -> AIMessage:
        step = super().next_step(messages)
        if step.tool_calls and step.tool_calls[0]["name"] in WRITES:
            first = step.tool_calls[0]
            return AIMessage(
                content="", tool_calls=[first, first | {"id": f"{first['id']}-again"}]
            )
        return step


class Recorder(StubModel):
    """The stub model, keeping the system prompt it was given."""

    system_prompt: str = ""

    def _generate(
        self, messages: list[BaseMessage], stop=None, run_manager=None, **kwargs
    ) -> ChatResult:
        self.system_prompt = self.system_prompt or messages[0].text
        return super()._generate(messages, stop, run_manager, **kwargs)


def claim(client, claim_id="CLM-1001"):
    return client.get(f"/api/claims/{claim_id}").json()


def steps(client, claim_id="CLM-1001"):
    return client.get(f"/api/claims/{claim_id}/steps").json()


def test_the_stub_works_a_small_claim_through_every_tool(client):
    result = main.run("CLM-1001", "thread-1", StubModel())
    assert result.startswith("CLM-1001: approve, $420.00, now decided")
    worked = claim(client)
    assert worked["status"] == "decided"
    assert worked["payment"]["amount"] == 420.0
    assert worked["decision"]["reason"] == REASON
    recorded = steps(client)
    assert [s["kind"] for s in recorded] == ["tool_call", "tool_result"] * 7 + [
        "message"
    ]
    assert {s["thread_id"] for s in recorded} == {"thread-1"}
    assert [s["text"] for s in recorded if s["kind"] == "tool_call"] == [
        "Read the claim CLM-1001",
        "Read the policy POL-2001",
        "Read the premium plan",
        "Read the claim history of customer CUS-3001",
        "Read the policy wording",
        "Record the decision: approve, $420.00, citing section 10",
        "Pay $420.00",
    ]
    assert recorded[-1]["text"] == "Approved CLM-1001 in full and paid it."


def test_a_payment_over_the_limit_is_refused_and_recorded(client):
    result = main.run("CLM-1002", "thread-1", StubModel())
    assert "now awaiting sign-off" in result
    worked = claim(client, "CLM-1002")
    assert worked["status"] == "awaiting_signoff"
    assert worked["payment"] is None
    refusals = [s for s in steps(client, "CLM-1002") if s["text"].startswith("Refused")]
    assert len(refusals) == 1
    assert refusals[0]["kind"] == "tool_result"
    assert refusals[0]["text"].startswith(
        "Refused (403): The payout of $1,150.00 is over the $1,000.00 limit"
    )
    assert steps(client, "CLM-1002")[-1]["text"].endswith(
        "The payment waits for a handler's sign-off."
    )


def test_a_model_that_stops_without_deciding_leaves_the_claim_waiting(client):
    model = scripted(
        tool_call("get_claim", claim_id="CLM-1001"), AIMessage("Not sure.")
    )
    result = main.run("CLM-1001", "thread-1", model)
    assert result == (
        "CLM-1001: no decision. The run ended without a decision. "
        "The claim is back in the queue."
    )
    assert claim(client)["status"] == "waiting"
    last = steps(client)[-1]
    assert (last["kind"], last["text"]) == (
        "error",
        "The run ended without a decision. The claim is back in the queue.",
    )


def test_an_approval_that_is_never_paid_is_dropped(client):
    model = scripted(
        tool_call(
            "record_decision",
            claim_id="CLM-1001",
            decision="approve",
            payout=420.0,
            reason=REASON,
            policy_section=3,
        ),
        AIMessage("Done."),
    )
    main.run("CLM-1001", "thread-1", model)
    worked = claim(client)
    assert worked["status"] == "waiting"
    assert worked["decision"] is None
    assert steps(client)[-1]["text"].startswith("The run ended without paying")


def test_a_model_that_fails_partway_leaves_the_claim_waiting(client):
    result = main.run("CLM-1001", "thread-1", Broken(fail_on=3))
    assert "The run failed: The model is down." in result
    assert claim(client)["status"] == "waiting"
    last = steps(client)[-1]
    assert last["kind"] == "error"
    assert last["text"] == (
        "The run failed: The model is down. The claim is back in the queue."
    )


def test_a_failure_after_the_decision_keeps_the_decision(client):
    main.run("CLM-1002", "thread-1", Broken(fail_on=7))
    worked = claim(client, "CLM-1002")
    assert worked["status"] == "awaiting_signoff"
    assert steps(client, "CLM-1002")[-1]["text"] == "The run failed: The model is down."


def test_a_claim_that_isnt_waiting_is_left_alone(client):
    client.post("/api/claims/CLM-1001/start", json={"thread_id": "other-run"})
    with pytest.raises(main.Refused, match="CLM-1001 is in progress"):
        main.run("CLM-1001", "thread-1", StubModel())
    assert claim(client)["thread_id"] == "other-run"
    assert steps(client) == []


def test_the_same_write_twice_at_once_is_refused_once(client):
    result = main.run("CLM-1001", "thread-1", Twice())
    assert result.startswith("CLM-1001: approve, $420.00, now decided")
    assert claim(client)["payment"]["amount"] == 420.0
    recorded = steps(client)
    refusals = sorted(s["text"] for s in recorded if s["text"].startswith("Refused"))
    assert refusals == [
        "Refused (409): CLM-1001 already has a decision.",
        "Refused (409): CLM-1001 has already been paid.",
    ]
    assert [s for s in recorded if s["kind"] == "error"] == []


def test_an_error_that_isnt_json_comes_back_as_text(monkeypatch):
    failing = httpx.MockTransport(
        lambda _: httpx.Response(500, text="Internal Server Error")
    )
    monkeypatch.setattr(
        main, "backend", lambda: httpx.Client(base_url="http://test", transport=failing)
    )
    with pytest.raises(main.Refused, match=r"^Refused \(500\): Internal Server Error$"):
        main.call("GET", "/api/claims/CLM-1001")


def test_a_run_without_a_model_puts_the_claim_back(client, monkeypatch):
    monkeypatch.delenv("MODEL_NAME", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    result = main.run("CLM-1001", "thread-1")
    assert "The run failed: 'OPENROUTER_API_KEY'" in result
    assert claim(client)["status"] == "waiting"
    assert steps(client)[-1]["kind"] == "error"


def test_the_agent_has_exactly_its_seven_tools():
    assert [t.name for t in main.TOOLS] == [
        "get_claim",
        "get_policy",
        "get_plan",
        "get_claim_history",
        "get_policy_wording",
        "record_decision",
        "pay_claim",
    ]
    assert all(t.handle_tool_error for t in main.TOOLS)


def test_the_system_prompt_comes_from_the_backend(tmp_path, monkeypatch):
    instructions = tmp_path / "instructions.md"
    instructions.write_text("Custom instructions for this test.", encoding="utf-8")
    monkeypatch.setattr(backend_main, "INSTRUCTIONS", instructions)
    model = Recorder()
    main.run("CLM-1001", "thread-1", model)
    assert model.system_prompt == "Custom instructions for this test."


def test_the_agent_never_imports_the_backend():
    for module in AGENT.glob("*.py"):
        tree = ast.parse(module.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            assert not any(n.split(".")[0] == "backend" for n in names), module.name


def test_model_choice(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.delenv("MODEL_NAME", raising=False)
    default = main.model()
    assert isinstance(default, ChatOpenAI)
    assert default.model_name == "openai/gpt-6-luna"
    assert default.reasoning_effort == "low"
    monkeypatch.setenv("MODEL_NAME", "openrouter/free")
    chosen = main.model()
    assert isinstance(chosen, ChatOpenAI)
    assert chosen.model_name == "openrouter/free"
    assert chosen.reasoning_effort is None
    monkeypatch.setenv("MODEL_NAME", "stub")
    assert isinstance(main.model(), StubModel)


def test_the_environment_wins_over_dotenv(tmp_path, monkeypatch):
    dotenv_file = tmp_path / ".env"
    dotenv_file.write_text("MODEL_NAME=from-dotenv\nUNDERCOVER_ONLY_IN_DOTENV=yes\n")
    monkeypatch.setattr("dotenv.main.find_dotenv", lambda *_, **__: str(dotenv_file))
    monkeypatch.setenv("MODEL_NAME", "from-environment")
    monkeypatch.delenv("UNDERCOVER_ONLY_IN_DOTENV", raising=False)
    importlib.reload(main)
    assert main.os.environ["MODEL_NAME"] == "from-environment"
    assert main.os.environ["UNDERCOVER_ONLY_IN_DOTENV"] == "yes"


def test_a_silent_final_reply_still_ends_the_run(client):
    main.run("CLM-1001", "thread-1", scripted(AIMessage("")))
    recorded = steps(client)
    assert [s["kind"] for s in recorded] == ["message", "error"]
    assert recorded[0]["text"] == "The agent finished without a closing note."


def test_describe_falls_back_to_the_raw_call():
    assert main.describe("other_tool", {"x": 1}) == 'other_tool {"x": 1}'
    assert main.describe("pay_claim", {"amount": "lots"}) == "Pay lots"


def test_backend_url(monkeypatch):
    monkeypatch.undo()
    monkeypatch.setenv("BACKEND_URL", "http://127.0.0.1:8001")
    assert str(main.backend().base_url) == "http://127.0.0.1:8001"


def test_command_line(monkeypatch, capsys):
    monkeypatch.setenv("MODEL_NAME", "stub")
    assert cli(["CLM-1001"]) == 0
    assert "CLM-1001: approve, $420.00, now decided" in capsys.readouterr().out
    assert cli([]) == 2
    assert capsys.readouterr().out.startswith("Usage:")
