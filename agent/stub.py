"""A scripted model for tests: it approves each claim in full, with no model call."""

import json
from collections.abc import Sequence
from typing import Any

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult

REASON = "The stub model approves every claim in full. It is only for tests."


class StubModel(BaseChatModel):
    """Reads the claim, approves the amount claimed, pays it, then replies."""

    @property
    def _llm_type(self) -> str:
        return "stub"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        return ChatResult(generations=[ChatGeneration(message=reply(messages))])


def tool_call(name: str, args: dict, messages: Sequence[BaseMessage]) -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[{"name": name, "args": args, "id": f"call-{len(messages)}"}],
    )


def reply(messages: Sequence[BaseMessage]) -> AIMessage:
    results = {m.name: m.text for m in messages if isinstance(m, ToolMessage)}
    if "get_claim" not in results:
        return tool_call("get_claim", {}, messages)
    amount = json.loads(results["get_claim"])["amount_claimed"]
    if "record_decision" not in results:
        decision = {
            "decision": "approve",
            "payout": amount,
            "reason": REASON,
            "policy_section": "None, test run",
        }
        return tool_call("record_decision", decision, messages)
    if "pay_claim" not in results:
        return tool_call("pay_claim", {"amount": amount}, messages)
    return AIMessage(content=f"Approved, payout ${amount:,.2f}.")
