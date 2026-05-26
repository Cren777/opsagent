import pytest

pytest.importorskip("fastapi")

from ops_agent.api.routes.chat import ChatRequest


def test_chat_request_accepts_log_attachments():
    request = ChatRequest(
        query="帮我分析这个日志",
        attachments=[{"id": "log_123", "type": "log", "filename": "error.log"}],
    )

    assert request.attachments[0]["id"] == "log_123"


def test_log_attachment_forces_fault_troubleshooting_intent():
    from ops_agent.core.intent.types import IntentType
    from ops_agent.core.orchestrator import Orchestrator

    intent = Orchestrator._resolve_intent_for_attachments(
        IntentType.KNOWLEDGE_QUERY,
        [{"id": "log_123", "type": "log", "filename": "error.log"}],
    )

    assert intent == IntentType.FAULT_TROUBLESHOOTING
