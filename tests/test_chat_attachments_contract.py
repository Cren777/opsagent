import pytest
import inspect

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


def test_merge_auto_resolved_log_attachments_deduplicates():
    from ops_agent.core.orchestrator import Orchestrator

    merged = Orchestrator._merge_log_attachments(
        [{"id": "log_123", "type": "log", "filename": "error.log"}],
        [
            {"id": "log_123", "type": "log", "filename": "error.log"},
            {"id": "local_456", "type": "log", "filename": "ops_agent_2026-05-25.log"},
        ],
    )

    assert [item["id"] for item in merged] == ["log_123", "local_456"]


def test_data_analysis_handler_accepts_router_extra_kwargs():
    from ops_agent.core.orchestrator import Orchestrator

    signature = inspect.signature(Orchestrator._handle_data_analysis)

    assert any(param.kind == inspect.Parameter.VAR_KEYWORD for param in signature.parameters.values())
