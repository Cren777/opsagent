"""Index management routes."""
from fastapi import APIRouter
from pydantic import BaseModel

from ops_agent.models.indexing.index_service import IndexService

router = APIRouter(prefix="/api/indexes", tags=["索引管理"])


class LogRebuildRequest(BaseModel):
    path: str | None = None


@router.get("/status")
async def get_index_status():
    return IndexService().status()


@router.post("/knowledge/rebuild")
async def rebuild_knowledge_index():
    return IndexService().rebuild_knowledge()


@router.post("/logs/rebuild")
async def rebuild_log_index(payload: LogRebuildRequest):
    return IndexService().rebuild_logs(path=payload.path)


@router.post("/{collection}/clear")
async def clear_index_collection(collection: str):
    return IndexService().clear_collection(collection)
