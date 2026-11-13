"""A scripted model for tests: it reads, approves in full and tries to pay."""

import json
import re
from typing import Any

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult

REASON = (
    "This is the stub model, which approves every claim in full for testing. "
    "It is not a real assessment of the claim."
)


def tool_call(name: str, **args: Any) -> AIMessage:
    return AIMessage(
        content="", tool_calls=[{"name": name, "args": args, "id": f"stub-{name}"}]
    )


class StubModel(BaseChatModel):
    """Works a claim the same way every time, without calling a real model."""

    @property
    def _llm_type(self) -> str:
        return "undercover-stub"

    def bind_tools(self, tools: Any, **kwargs: Any) -> "StubModel":
        return self

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        return ChatResult(
            generations=[ChatGeneration(message=self.next_step(messages))]
        )

    def next_step(self, messages: list[BaseMessage]) -> AIMessage:
        """Call the next tool in the script, or finish once every tool has run."""
        request = next(m.text for m in messages if isinstance(m, HumanMessage))
        claim_id = re.findall(r"CLM-\d+", request)[0]
        results = {m.name: m.text for m in messages if isinstance(m, ToolMessage)}
        claim = json.loads(results.get("get_claim", "{}"))
        policy = json.loads(results.get("get_policy", "{}"))
        script = [
            ("get_claim", lambda: tool_call("get_claim", claim_id=claim_id)),
            (
                "get_policy",
                lambda: tool_call("get_policy", policy_id=claim["policy_id"]),
            ),
            ("get_plan", lambda: tool_call("get_plan", plan=policy["plan"])),
            (
                "get_claim_history",
                lambda: tool_call(
                    "get_claim_history", customer_id=claim["customer_id"]
                ),
            ),
            ("get_policy_wording", lambda: tool_call("get_policy_wording")),
            (
                "record_decision",
                lambda: tool_call(
                    "record_decision",
                    claim_id=claim_id,
                    decision="approve",
                    payout=claim["amount_claimed"],
                    reason=REASON,
                    policy_section=10,
                ),
            ),
            (
                "pay_claim",
                lambda: tool_call(
                    "pay_claim", claim_id=claim_id, amount=claim["amount_claimed"]
                ),
            ),
        ]
        for name, step in script:
            if name not in results:
                return step()
        if results["pay_claim"].startswith("Refused"):
            return AIMessage(
                content=f"Approved {claim_id} in full. The payment waits for a "
                "handler's sign-off."
            )
        return AIMessage(content=f"Approved {claim_id} in full and paid it.")
