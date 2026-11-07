"""The UnderCover Agent."""

import json
import os
from typing import Literal

import httpx
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.tools import BaseTool, tool
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from agent.stub import StubModel

load_dotenv(override=True)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "openai/gpt-6-luna"


def backend() -> httpx.Client:
    """Return a client for the UnderCover backend, at BACKEND_URL if set."""
    url = os.getenv("BACKEND_URL", "http://localhost:8000")
    return httpx.Client(base_url=url, timeout=30)


def call(method: str, path: str, body: dict | None = None) -> str:
    """Call the backend and return its reply, errors included, for the model."""
    with backend() as client:
        return client.request(method, path, json=body).text


def tools_for(claim_id: str) -> list[BaseTool]:
    """Return the agent's tools, bound to the claim it is working on."""

    @tool
    def get_claim() -> str:
        """Get the claim: the customer's story, the items claimed and the documents."""
        return call("GET", f"/api/claims/{claim_id}")

    @tool
    def get_policy(policy_id: str) -> str:
        """Get a policy: its plan, add-ons, purchase date, trip and travelers."""
        return call("GET", f"/api/policies/{policy_id}")

    @tool
    def get_plan(plan: str) -> str:
        """Get a plan's limits, waiting periods and deductible, such as 'premium'."""
        return call("GET", f"/api/plans/{plan}")

    @tool
    def get_claim_history(customer_id: str) -> str:
        """Get the customer's earlier claims."""
        return call("GET", f"/api/customers/{customer_id}/claims")

    @tool
    def get_policy_wording() -> str:
        """Get the policy wording, the contract that decisions follow."""
        return call("GET", "/api/policy-wording")

    @tool
    def record_decision(
        decision: Literal["approve", "decline", "refer"],
        payout: float,
        reason: str,
        policy_section: str,
    ) -> str:
        """Record the decision: the payout (0 unless approved), a reason of two or
        three sentences and the policy section it rests on."""
        body = {
            "decision": decision,
            "payout": payout,
            "reason": reason,
            "policy_section": policy_section,
        }
        return call("POST", f"/api/claims/{claim_id}/decision", body)

    @tool
    def pay_claim(amount: float) -> str:
        """Pay the approved payout. Over $1,000 it waits for a handler's sign-off."""
        return call("POST", f"/api/claims/{claim_id}/payment", {"amount": amount})

    return [
        get_claim,
        get_policy,
        get_plan,
        get_claim_history,
        get_policy_wording,
        record_decision,
        pay_claim,
    ]


def model() -> BaseChatModel:
    """Return the model named in MODEL_NAME, or GPT-6 Luna by default."""
    name = os.getenv("MODEL_NAME")
    if name == "stub":
        return StubModel()
    return ChatOpenAI(
        model=name or DEFAULT_MODEL,
        base_url=OPENROUTER_BASE_URL,
        api_key=SecretStr(os.environ["OPENROUTER_API_KEY"]),
        reasoning_effort=None if name else "low",
    )


def steps(message: BaseMessage) -> list[tuple[str, str]]:
    """Turn one of the agent's messages into the steps the dashboard shows."""
    if isinstance(message, ToolMessage):
        return [("tool_result", f"{message.name}: {message.text}")]
    found = [("message", str(message.text))] if message.text else []
    if isinstance(message, AIMessage):
        found += [
            ("tool_call", f"{c['name']}({json.dumps(c['args'])})")
            for c in message.tool_calls
        ]
    return found


def record_step(claim_id: str, kind: str, text: str) -> None:
    with backend() as client:
        client.post(
            f"/api/claims/{claim_id}/steps", json={"kind": kind, "text": text}
        ).raise_for_status()


def run(claim_id: str, thread_id: str, llm: BaseChatModel | None = None) -> str:
    """Run the agent on one claim, recording each step, and return its reply."""
    with backend() as client:
        instructions = client.get("/api/instructions").raise_for_status().json()
        client.post(
            f"/api/claims/{claim_id}/start", json={"thread_id": thread_id}
        ).raise_for_status()
    agent = create_agent(
        llm or model(),
        tools=tools_for(claim_id),
        system_prompt=instructions["instructions"],
    )
    reply = ""
    updates = agent.stream(
        {"messages": [{"role": "user", "content": f"Please decide claim {claim_id}."}]},
        config={"configurable": {"thread_id": thread_id}},
        stream_mode="updates",
    )
    for update in updates:
        for state in update.values():
            for message in state["messages"]:
                for kind, text in steps(message):
                    record_step(claim_id, kind, text)
                if isinstance(message, AIMessage):
                    reply = message.text
    return reply
