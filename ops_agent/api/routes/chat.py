"""聊天接口"""
import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from loguru import logger

from ops_agent.core.orchestrator import Orchestrator
from ops_agent.api.services.llm_factory import get_dynamic_llm_client

router = APIRouter()


class ChatRequest(BaseModel):
    query: str
    history: list[dict] = []


class ChatResponse(BaseModel):
    answer: str
    intent: str = ""
    sources: list[dict] = []
    sql: str = ""


# 优先使用配置数据库中的 LLM 提供商，回退到 settings 默认
_orchestrator = Orchestrator(llm_client=get_dynamic_llm_client())


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """非流式对话接口"""
    try:
        result = await _orchestrator.process(req.query)
        return ChatResponse(
            answer=result.get("answer", ""),
            intent=result.get("intent", ""),
            sources=result.get("sources", []),
            sql=result.get("sql", ""),
        )
    except Exception as e:
        logger.exception("Chat 处理失败")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    """SSE 流式对话接口"""
    async def event_generator():
        try:
            async for event in _orchestrator.process_stream(req.query):
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
