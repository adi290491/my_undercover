"""The UnderCover Agent: it decides a claim through the backend's API."""

import json
import os
import uuid
from collections import defaultdict
from collections.abc import Iterator
from typing import Any, Literal

import httpx
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.tools import BaseTool, ToolException, tool
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from agent.stub import StubModel

load_dotenv()

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "openai/gpt-6-luna"


class Refused(ToolException):
    """The backend refused a request; the agent reads the reason as a tool result."""


def backend() -> httpx.Client:
    """Return a client for the UnderCover backend at BACKEND_URL."""
    url = os.environ.get("BACKEND_URL") or "http://127.0.0.1:8000"
    return httpx.Client(base_url=url, timeout=30)


def call(method: str, path: str, body: dict[str, Any] | None = None) -> Any:
    """Call the backend and return its JSON, raising Refused when it says no."""
    with backend() as client:
        response = client.request(method, path, json=body)
    if response.is_error:
        detail = response.json().get("detail")
        raise Refused(f"Refused ({response.status_code}): {detail}")
    return response.json()


def dumps(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False)


@tool
def get_claim(claim_id: str) -> str:
    """Get one claim in full: the story, the items claimed and the documents."""
    return dumps(call("GET", f"/api/claims/{claim_id}"))


@tool
def get_policy(policy_id: str) -> str:
    """Get a policy: its plan, add-ons, purchase date, trip dates and travelers."""
    return dumps(call("GET", f"/api/policies/{policy_id}"))


@tool
def get_plan(plan: str) -> str:
    """Get a plan's limits, waiting periods and deductible, such as premium."""
    return dumps(call("GET", f"/api/plans/{plan}"))


@tool
def get_claim_history(customer_id: str) -> str:
    """List a customer's earlier claims."""
    return dumps(call("GET", f"/api/customers/{customer_id}/claims"))


@tool
def get_policy_wording() -> str:
    """Get the policy wording, the contract that every decision follows."""
    return call("GET", "/api/policy-wording")["text"]


@tool
def record_decision(
    claim_id: str,
    decision: Literal["approve", "decline", "refer"],
    payout: float,
    reason: str,
    policy_section: int,
) -> str:
    """Record the decision: the payout in US dollars (0 unless approved), a reason of
    two or three sentences, and the number of the policy wording section it rests on."""
    body = {
        "decision": decision,
        "payout": payout,
        "reason": reason,
        "policy_section": policy_section,
    }
    return dumps(call("POST", f"/api/claims/{claim_id}/decision", body))


@tool
def pay_claim(claim_id: str, amount: float) -> str:
    """Pay an approved claim its payout. A payout over $1,000 waits for a sign-off."""
    return dumps(call("POST", f"/api/claims/{claim_id}/payment", {"amount": amount}))


TOOLS: list[BaseTool] = [
    get_claim,
    get_policy,
    get_plan,
    get_claim_history,
    get_policy_wording,
    record_decision,
    pay_claim,
]
for each in TOOLS:
    each.handle_tool_error = True


def model() -> BaseChatModel:
    """Return the model in MODEL_NAME, the stub for MODEL_NAME=stub, or GPT-6 Luna."""
    name = os.getenv("MODEL_NAME")
    if name == "stub":
        return StubModel()
    return ChatOpenAI(
        model=name or DEFAULT_MODEL,
        base_url=OPENROUTER_BASE_URL,
        api_key=SecretStr(os.environ["OPENROUTER_API_KEY"]),
        reasoning_effort=None if name else "low",
    )


STATUS_WORDS = {
    "waiting": "waiting",
    "in_progress": "in progress",
    "awaiting_signoff": "awaiting sign-off",
    "decided": "decided",
}

STEP_WORDS = {
    "get_claim": "Read the claim {claim_id}",
    "get_policy": "Read the policy {policy_id}",
    "get_plan": "Read the {plan} plan",
    "get_claim_history": "Read the claim history of customer {customer_id}",
    "get_policy_wording": "Read the policy wording",
    "record_decision": (
        "Record the decision: {decision}, {payout}, citing section {policy_section}"
    ),
    "pay_claim": "Pay {amount}",
}


def money(value: Any) -> str:
    return f"${value:,.2f}" if isinstance(value, int | float) else str(value)


def describe(name: str, args: dict[str, Any]) -> str:
    """Put a tool call in plain words, for the steps the handlers read."""
    words = STEP_WORDS.get(name)
    if words is None:
        return f"{name} {dumps(args)}"
    shown = {k: money(v) if k in ("payout", "amount") else v for k, v in args.items()}
    return words.format_map(defaultdict(lambda: "?", shown))


def add_step(claim_id: str, thread_id: str, kind: str, text: str) -> None:
    body = {"thread_id": thread_id, "kind": kind, "text": text}
    call("POST", f"/api/claims/{claim_id}/steps", body)


def record(claim_id: str, thread_id: str, message: BaseMessage) -> None:
    """Post one message from the agent's run as steps the dashboard shows.

    Every run ends with a message step (the agent's final reply) or an error step
    (from run() when the run fails), so the dashboard knows when a run is over."""
    if isinstance(message, ToolMessage):
        add_step(claim_id, thread_id, "tool_result", message.text)
    elif isinstance(message, AIMessage):
        if message.text or not message.tool_calls:
            text = message.text or "The agent finished without a closing note."
            add_step(claim_id, thread_id, "message", text)
        for tool_call in message.tool_calls:
            text = describe(tool_call["name"], tool_call["args"])
            add_step(claim_id, thread_id, "tool_call", text)


def work(claim_id: str, thread_id: str, instructions: str, llm: BaseChatModel) -> None:
    """Stream the agent on a started claim, recording each step as it happens."""
    agent = create_agent(llm, tools=TOOLS, system_prompt=instructions)
    updates = agent.stream(
        {"messages": [{"role": "user", "content": f"Work claim {claim_id}."}]},
        config={"configurable": {"thread_id": thread_id}, "recursion_limit": 40},
        stream_mode="updates",
    )
    for update in updates:
        for node in update.values():
            for message in node["messages"]:
                record(claim_id, thread_id, message)


def outcome(claim: dict[str, Any], problem: str | None) -> str:
    """Say in a line or two how a run left the claim."""
    claim_id, decision = claim["claim_id"], claim["decision"]
    if decision is None:
        return f"{claim_id}: no decision. {problem}"
    section = decision["policy_section"]
    lines = [
        f"{claim_id}: {decision['decision']}, {money(decision['payout'])}, "
        f"now {STATUS_WORDS[claim['status']]}",
        f"Section {section['number']}, {section['title']}: {decision['reason']}",
    ]
    return "\n".join(lines + ([problem] if problem else []))


def run(claim_id: str, thread_id: str, llm: BaseChatModel | None = None) -> str:
    """Work one claim with the agent, and return how it ended."""
    llm = llm or model()
    instructions = call("GET", "/api/instructions")["text"]
    call("POST", f"/api/claims/{claim_id}/start", {"thread_id": thread_id})
    problem = None
    try:
        work(claim_id, thread_id, instructions, llm)
    except Exception as error:  # a failed run must never leave the claim half done
        problem = f"The run failed: {error}"
    claim = call("GET", f"/api/claims/{claim_id}")
    if claim["status"] == "in_progress":
        unfinished = (
            "The run ended without paying the approval."
            if claim["decision"]
            else "The run ended without a decision."
        )
        problem = f"{problem or unfinished} The claim is back in the queue."
        add_step(claim_id, thread_id, "error", problem)
        claim = call(
            "POST", f"/api/claims/{claim_id}/release", {"thread_id": thread_id}
        )
    elif problem:
        add_step(claim_id, thread_id, "error", problem)
    return outcome(claim, problem)


def work_queue(llm: BaseChatModel | None = None) -> Iterator[str]:
    """Work every waiting claim in turn, saying how each one ended."""
    for claim in call("GET", "/api/claims"):
        if claim["status"] != "waiting":
            continue
        try:
            yield run(claim["claim_id"], str(uuid.uuid4()), llm)
        except Refused as refusal:  # another run took the claim since the list
            yield f"{claim['claim_id']}: skipped. {refusal}"
