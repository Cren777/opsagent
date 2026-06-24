import pytest
from pydantic import ValidationError

from fastapi import FastAPI
from fastapi.testclient import TestClient

from ops_agent.api.dependencies import auth
from ops_agent.api.routes import chat as chat_routes


SUGGESTION_TEXT = "\u7ee7\u7eed\u6392\u67e5\u5417\uff1f"


class FakeSuggestionService:
    def __init__(self):
        self.calls = []

    async def suggest(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "mode": kwargs["mode"],
            "source": "llm",
            "suggestions": [SUGGESTION_TEXT],
        }


def build_client(*, authenticated: bool):
    app = FastAPI()
    app.include_router(chat_routes.router, prefix="/api")

    service = FakeSuggestionService()
    app.dependency_overrides[chat_routes.get_question_suggestion_service] = (
        lambda: service
    )
    if authenticated:
        app.dependency_overrides[auth.get_current_user] = (
            lambda: {"id": "user-1", "username": "tester"}
        )

    return TestClient(app), service


def test_suggestions_requires_login():
    client, _ = build_client(authenticated=False)

    response = client.post(
        "/api/chat/suggestions",
        json={"mode": "context", "history": []},
    )

    assert response.status_code == 401


def test_suggestions_forwards_validated_context():
    client, service = build_client(authenticated=True)
    payload = {
        "mode": "completion",
        "draft": "continue checking nginx errors",
        "history": [
            {
                "role": "user",
                "content": "nginx 502",
                "intent": "fault_troubleshooting",
            },
            {
                "role": "assistant",
                "content": "Check upstream timeout first.",
                "sql": "select 1",
            },
        ],
        "datasource_id": "prod-clickhouse",
        "attachments": [{"type": "log", "filename": "nginx-error.log"}],
        "limit": 5,
    }

    response = client.post("/api/chat/suggestions", json=payload)

    assert response.status_code == 200
    assert response.json() == {
        "mode": "completion",
        "source": "llm",
        "suggestions": [SUGGESTION_TEXT],
    }
    assert service.calls == [
        {
            "mode": "completion",
            "draft": "continue checking nginx errors",
            "history": [
                {
                    "role": "user",
                    "content": "nginx 502",
                    "sql": None,
                    "intent": "fault_troubleshooting",
                },
                {
                    "role": "assistant",
                    "content": "Check upstream timeout first.",
                    "sql": "select 1",
                    "intent": None,
                },
            ],
            "datasource_id": "prod-clickhouse",
            "attachments": [{"type": "log", "filename": "nginx-error.log"}],
            "limit": 5,
        }
    ]


def test_context_mode_rejects_non_empty_draft():
    client, service = build_client(authenticated=True)

    response = client.post(
        "/api/chat/suggestions",
        json={"mode": "context", "draft": "abc"},
    )

    assert response.status_code == 422
    assert service.calls == []


def test_completion_mode_rejects_blank_draft():
    client, service = build_client(authenticated=True)

    response = client.post(
        "/api/chat/suggestions",
        json={"mode": "completion", "draft": "   "},
    )

    assert response.status_code == 422
    assert service.calls == []

def test_response_model_rejects_oversized_suggestions():
    with pytest.raises(ValidationError):
        chat_routes.QuestionSuggestionResponse(
            mode="context",
            source="fallback",
            suggestions=["x"] * 9,
        )

    with pytest.raises(ValidationError):
        chat_routes.QuestionSuggestionResponse(
            mode="context",
            source="fallback",
            suggestions=["x" * 121],
        )

def test_suggestions_rejects_oversized_prompt_metadata():
    client, service = build_client(authenticated=True)

    cases = [
        {"mode": "context", "datasource_id": "d" * 129},
        {"mode": "context", "history": [{"role": "user", "content": "x", "intent": "i" * 65}]},
        {"mode": "context", "history": [{"role": "assistant", "content": "x", "sql": "s" * 2001}]},
        {"mode": "context", "attachments": [{"type": "log", "filename": "f" * 256}]},
        {"mode": "context", "attachments": [{"type": "log", "filename": "a.log", "path": "secret"}]},
    ]

    for payload in cases:
        response = client.post("/api/chat/suggestions", json=payload)
        assert response.status_code == 422

    assert service.calls == []

def test_existing_chat_route_keeps_dict_attachments(monkeypatch):
    captured = {}

    class FakeOrchestrator:
        async def process(self, _query, **kwargs):
            captured.update(kwargs)
            return {"answer": "ok"}

    monkeypatch.setattr(chat_routes, "get_orchestrator", lambda: FakeOrchestrator())
    client, _ = build_client(authenticated=True)
    attachment = {"id": "log-1", "type": "log", "filename": "app.log"}

    response = client.post("/api/chat", json={"query": "check", "attachments": [attachment]})

    assert response.status_code == 200
    assert captured["attachments"] == [attachment]
