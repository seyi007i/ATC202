"""FastAPI route tests using TestClient with the agent loop faked out."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import config
from app.dependencies import get_agent_loop
from app.main import app
from app.models import AnthropicTimeoutError, ChatResponse, EscalationWriteError, SafeBankError


class _FakeAgentLoop:
    def __init__(self, response: ChatResponse | None = None, error: Exception | None = None) -> None:
        self._response = response
        self._error = error
        self.calls: list[tuple[str, str]] = []

    def run_turn(self, session_id: str, message: str) -> ChatResponse:
        self.calls.append((session_id, message))
        if self._error is not None:
            raise self._error
        return self._response


def _override_loop(fake_loop: _FakeAgentLoop) -> None:
    app.dependency_overrides[get_agent_loop] = lambda: fake_loop


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "test-key-for-suite")
    # raise_server_exceptions=False: lets us assert on the 500 response body
    # produced by our global exception handler instead of the TestClient
    # re-raising the original exception for interactive debugging.
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_home_page_renders(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "SafeBank Companion" in response.text


def test_chat_page_renders(client):
    response = client.get("/chat")
    assert response.status_code == 200
    assert "chat-window" in response.text


def test_health_check(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_endpoint_happy_path(client):
    fake_response = ChatResponse(reply="Looks safe to me.", suggested_actions=["Stay alert."])
    _override_loop(_FakeAgentLoop(response=fake_response))

    response = client.post("/api/chat", json={"session_id": "s1", "message": "Is this a scam?"})

    assert response.status_code == 200
    body = response.json()
    assert body["reply"] == "Looks safe to me."
    assert body["fraud_assessment"] is None
    assert body["suggested_actions"] == ["Stay alert."]


def test_chat_endpoint_rejects_blank_message(client):
    response = client.post("/api/chat", json={"session_id": "s1", "message": "   "})
    assert response.status_code == 422


def test_chat_endpoint_rejects_missing_session_id(client):
    response = client.post("/api/chat", json={"message": "hello"})
    assert response.status_code == 422


def test_chat_endpoint_upstream_failure_returns_friendly_502(client):
    _override_loop(_FakeAgentLoop(error=AnthropicTimeoutError("timed out")))
    response = client.post("/api/chat", json={"session_id": "s1", "message": "hello"})
    assert response.status_code == 502
    assert "try again" in response.json()["detail"].lower()


def test_chat_endpoint_escalation_write_failure_returns_friendly_502(client):
    _override_loop(_FakeAgentLoop(error=EscalationWriteError("disk full")))
    response = client.post("/api/chat", json={"session_id": "s1", "message": "hello"})
    assert response.status_code == 502
    assert "contact your bank" in response.json()["detail"].lower()


def test_chat_endpoint_unexpected_safebank_error_returns_500(client):
    _override_loop(_FakeAgentLoop(error=SafeBankError("weird internal error")))
    response = client.post("/api/chat", json={"session_id": "s1", "message": "hello"})
    assert response.status_code == 500


def test_chat_endpoint_unhandled_exception_returns_friendly_500(client):
    _override_loop(_FakeAgentLoop(error=RuntimeError("boom")))
    response = client.post("/api/chat", json={"session_id": "s1", "message": "hello"})
    assert response.status_code == 500
    assert "went wrong" in response.json()["detail"].lower()
