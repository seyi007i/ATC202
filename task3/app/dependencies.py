"""FastAPI dependency providers.

Each provider is memoized with ``lru_cache`` so the app builds one
shared instance of each collaborator per process (a `.env`-backed local
demo app, not a horizontally-scaled service). Tests override
``get_agent_loop`` via ``app.dependency_overrides`` so no provider here
is ever exercised against the real Anthropic API in the test suite.
"""

from __future__ import annotations

from functools import lru_cache

from app import config
from app.agent_loop import AgentLoop
from app.anthropic_client import AnthropicAgentClient
from app.conversation import ConversationManager
from app.escalation import EscalationStore


@lru_cache
def get_main_client() -> AnthropicAgentClient:
    """Return the shared main-conversation Anthropic client."""
    return AnthropicAgentClient(model=config.MAIN_MODEL)


@lru_cache
def get_subagent_client() -> AnthropicAgentClient:
    """Return the shared fraud-analysis subagent Anthropic client."""
    return AnthropicAgentClient(model=config.SUBAGENT_MODEL)


@lru_cache
def get_conversation_manager() -> ConversationManager:
    """Return the shared conversation manager (reuses the main client to summarize)."""
    return ConversationManager(summarizer_client=get_main_client())


@lru_cache
def get_escalation_store() -> EscalationStore:
    """Return the shared escalation store."""
    return EscalationStore()


@lru_cache
def get_agent_loop() -> AgentLoop:
    """Return the shared agent loop tying all collaborators together."""
    return AgentLoop(
        main_client=get_main_client(),
        subagent_client=get_subagent_client(),
        conversation_manager=get_conversation_manager(),
        escalation_store=get_escalation_store(),
    )
