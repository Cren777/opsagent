"""Knowledge base management routes."""
from fastapi import APIRouter, HTTPException, Query, Request

from ops_agent.models.knowledge.knowledge_service import KnowledgeService

router = APIRouter(prefix="/api/knowledge", tags=["知识库"])


@router.get("/files")
async def list_knowledge_files():
    return KnowledgeService().list_files()


@router.post("/upload")
async def upload_knowledge_file(
    request: Request,
    filename: str = Query(..., description="Relative filename under data/knowledge"),
):
    try:
        return KnowledgeService().save_file(filename, await request.body())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/files/{file_id}")
async def get_knowledge_file(file_id: str):
    try:
        return KnowledgeService().get_file(file_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail="知识文件不存在") from e


@router.delete("/files/{file_id}")
async def delete_knowledge_file(file_id: str):
    return {"deleted": KnowledgeService().delete_file(file_id)}


@router.post("/reindex")
async def rebuild_knowledge_index():
    return KnowledgeService().rebuild_index()
