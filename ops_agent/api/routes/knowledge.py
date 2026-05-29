"""Knowledge base management routes."""
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from ops_agent.models.knowledge.knowledge_service import KnowledgeService

router = APIRouter(prefix="/api/knowledge", tags=["知识库"])


class FolderRequest(BaseModel):
    path: str


class RenameFolderRequest(BaseModel):
    path: str
    new_name: str


@router.get("/files")
async def list_knowledge_files():
    return KnowledgeService().list_files()


@router.get("/tree")
async def get_knowledge_tree():
    return KnowledgeService().get_tree()


@router.post("/folders")
async def create_knowledge_folder(payload: FolderRequest):
    try:
        return KnowledgeService().create_folder(payload.path)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.delete("/folders")
async def delete_knowledge_folder(path: str, recursive: bool = Query(default=False)):
    try:
        return {"deleted": KnowledgeService().delete_folder(path, recursive=recursive)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.put("/folders/rename")
async def rename_knowledge_folder(payload: RenameFolderRequest):
    try:
        return KnowledgeService().rename_folder(payload.path, payload.new_name)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail="知识文件夹不存在") from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/upload")
async def upload_knowledge_file(
    request: Request,
    filename: str = Query(..., description="Relative filename under data/knowledge"),
    folder: str = Query(default="", description="Target folder under data/knowledge"),
):
    try:
        return KnowledgeService().save_file_to_folder(folder, filename, await request.body())
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
