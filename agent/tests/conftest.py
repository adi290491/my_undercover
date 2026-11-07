import pytest
from fastapi.testclient import TestClient
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from agent import main
from backend.db import seed
from backend.main import app


class ScriptedModel(GenericFakeChatModel):
    """A chat model that gives scripted replies in place of a real model."""

    def bind_tools(self, tools, **kwargs):
        return self


def scripted(*calls: tuple[str, dict], reply: str = "Done.") -> ScriptedModel:
    messages = [
        AIMessage(content="", tool_calls=[{"name": n, "args": a, "id": str(i)}])
        for i, (n, a) in enumerate(calls)
    ]
    return ScriptedModel(messages=iter([*messages, AIMessage(content=reply)]))


@pytest.fixture(autouse=True)
def backend(tmp_path, monkeypatch):
    monkeypatch.setenv("UNDERCOVER_DB", str(tmp_path / "test.db"))
    seed()
    client = TestClient(app)
    monkeypatch.setattr(main, "backend", lambda: client)
    return client
