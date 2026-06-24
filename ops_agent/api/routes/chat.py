"""聊天接口"""
import json
from typing import Annotated, Literal, Optional

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, model_validator
from loguru import logger

from ops_agent.api.dependencies.auth import get_current_user
from ops_agent.core.question_suggestions import QuestionSuggestionService
from ops_agent.api.services.llm_factory import get_dynamic_llm_client

router = APIRouter()


class ChatRequest(BaseModel):
    query: str
    history: list[dict] = []
    datasource_id: Optional[str] = Field(default=None, max_length=128)
    attachments: list[dict] = []


class ChatResponse(BaseModel):
    answer: str
    intent: str = ""
    sources: list[dict] = []
    sql: str = ""
    diagnostics: dict = {}


SuggestionText = Annotated[str, Field(min_length=1, max_length=120)]


class SuggestionHistoryItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2000)
    sql: Optional[str] = Field(default=None, max_length=2000)
    intent: Optional[str] = Field(default=None, max_length=64)


class SuggestionAttachment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: Optional[str] = Field(default=None, max_length=128)
    type: str = Field(min_length=1, max_length=32)
    filename: Optional[str] = Field(default=None, max_length=255)
    size: Optional[int] = Field(default=None, ge=0, le=524_288_000)


class QuestionSuggestionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: Literal["context", "completion"]
    draft: str = Field(default="", max_length=500)
    history: list[SuggestionHistoryItem] = Field(default_factory=list, max_length=8)
    datasource_id: Optional[str] = Field(default=None, max_length=128)
    attachments: list[SuggestionAttachment] = Field(default_factory=list, max_length=8)
    limit: int = Field(default=6, ge=3, le=8)

    @model_validator(mode="after")
    def validate_mode_draft(self):
        if self.mode == "context" and self.draft.strip():
            raise ValueError("context mode requires empty draft")
        if self.mode == "completion" and not self.draft.strip():
            raise ValueError("completion mode requires non-empty draft")
        return self


class QuestionSuggestionResponse(BaseModel):
    mode: Literal["context", "completion"]
    source: Literal["llm", "fallback"]
    suggestions: list[SuggestionText] = Field(max_length=8)


def get_question_suggestion_service() -> QuestionSuggestionService:
    return QuestionSuggestionService(get_dynamic_llm_client())


# 优先使用配置数据库中的 LLM 提供商，回退到 settings 默认
_orchestrator = None


def get_orchestrator():
    global _orchestrator
    if _orchestrator is None:
        from ops_agent.core.orchestrator import Orchestrator

        _orchestrator = Orchestrator(llm_client=get_dynamic_llm_client())
    return _orchestrator


@router.post("/chat/suggestions", response_model=QuestionSuggestionResponse)
async def chat_suggestions(
    req: QuestionSuggestionRequest,
    current_user: dict = Depends(get_current_user),
    service: QuestionSuggestionService = Depends(get_question_suggestion_service),
):
    logger.info(
        "question_suggestions_api user_id={} mode={}",
        current_user.get("id"),
        req.mode,
    )
    result = await service.suggest(
        mode=req.mode,
        draft=req.draft,
        history=[item.model_dump() for item in req.history],
        datasource_id=req.datasource_id,
        attachments=[item.model_dump(exclude_none=True) for item in req.attachments],
        limit=req.limit,
    )
    return QuestionSuggestionResponse(**result)


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """非流式对话接口"""
    try:
        result = await get_orchestrator().process(
            req.query,
            datasource_id=req.datasource_id,
            history=req.history,
            attachments=req.attachments,
        )
        return ChatResponse(
            answer=result.get("answer", ""),
            intent=result.get("intent", ""),
            sources=result.get("sources", []),
            sql=result.get("sql", ""),
            diagnostics=result.get("diagnostics", {}),
        )
    except Exception as e:
        logger.exception("Chat 处理失败")
        return ChatResponse(
            answer=f"系统处理失败: {str(e)}。请稍后重试或检查系统配置。",
            intent="error",
        )


@router.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    """SSE 流式对话接口"""
    async def event_generator():
        try:
            async for event in get_orchestrator().process_stream(
                req.query,
                datasource_id=req.datasource_id,
                history=req.history,
                attachments=req.attachments,
            ):
                event_type = event.get("event", "message")
                data = event.get("data", {})
                yield f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.exception("Stream 处理失败")
            yield f"event: error\ndata: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
