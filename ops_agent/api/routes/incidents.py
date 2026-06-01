"""Log and incident case management routes."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ops_agent.models.troubleshooting.case_memory import IncidentCaseMemory
from ops_agent.models.uploads.log_upload_service import LogUploadService

router = APIRouter(prefix="/api", tags=["日志与案例"])


class CaseStatusUpdate(BaseModel):
    status: str


class CategoryUpdate(BaseModel):
    category: str


class CategoryCreate(BaseModel):
    name: str


class CategoryRename(BaseModel):
    old_name: str
    new_name: str


class CategoryPinUpdate(BaseModel):
    name: str
    pinned: bool


class CategoryDelete(BaseModel):
    name: str


@router.get("/logs")
async def list_uploaded_logs(
    query: str = "",
    category: str = "",
    source: str = "",
    severity: str = "",
):
    return LogUploadService().list_logs(
        query=query,
        category=category,
        source=source,
        severity=severity,
    )


@router.get("/logs/categories")
async def list_log_categories():
    return LogUploadService().category_summary()


@router.post("/logs/categories")
async def create_log_category(payload: CategoryCreate):
    try:
        return LogUploadService().create_category(payload.name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.put("/logs/categories/rename")
async def rename_log_category(payload: CategoryRename):
    try:
        return LogUploadService().rename_category(payload.old_name, payload.new_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.put("/logs/categories/pin")
async def pin_log_category(payload: CategoryPinUpdate):
    try:
        return LogUploadService().set_category_pinned(payload.name, payload.pinned)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.delete("/logs/categories")
async def delete_log_category(payload: CategoryDelete):
    try:
        return {"deleted": LogUploadService().delete_category(payload.name)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/logs/{file_id}")
async def get_uploaded_log(file_id: str):
    metadata = LogUploadService().get_metadata(file_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="日志不存在")
    return metadata


@router.get("/logs/{file_id}/preview")
async def preview_uploaded_log(file_id: str):
    try:
        return LogUploadService().preview_log(file_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail="日志不存在") from e


@router.put("/logs/{file_id}/category")
async def update_uploaded_log_category(file_id: str, payload: CategoryUpdate):
    try:
        return {"updated": LogUploadService().update_category(file_id, payload.category)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.delete("/logs/{file_id}")
async def delete_uploaded_log(file_id: str):
    return {"deleted": LogUploadService().delete_log(file_id)}


@router.get("/incidents")
async def list_incident_cases(
    status: str | None = None,
    query: str = "",
    category: str = "",
    symptom: str = "",
):
    return IncidentCaseMemory().list_cases(
        status=status,
        query=query,
        category=category,
        symptom=symptom,
    )


@router.get("/incidents/categories")
async def list_incident_categories():
    return IncidentCaseMemory().category_summary()


@router.post("/incidents/categories")
async def create_incident_category(payload: CategoryCreate):
    try:
        return IncidentCaseMemory().create_category(payload.name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.put("/incidents/categories/rename")
async def rename_incident_category(payload: CategoryRename):
    try:
        return IncidentCaseMemory().rename_category(payload.old_name, payload.new_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.put("/incidents/categories/pin")
async def pin_incident_category(payload: CategoryPinUpdate):
    try:
        return IncidentCaseMemory().set_category_pinned(payload.name, payload.pinned)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.delete("/incidents/categories")
async def delete_incident_category(payload: CategoryDelete):
    try:
        return {"deleted": IncidentCaseMemory().delete_category(payload.name)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/incidents/{case_id}")
async def get_incident_case(case_id: str):
    item = IncidentCaseMemory().get_case(case_id)
    if not item:
        raise HTTPException(status_code=404, detail="案例不存在")
    return item


@router.put("/incidents/{case_id}/status")
async def update_incident_status(case_id: str, payload: CaseStatusUpdate):
    return {"updated": IncidentCaseMemory().update_status(case_id, payload.status)}


@router.put("/incidents/{case_id}/category")
async def update_incident_category(case_id: str, payload: CategoryUpdate):
    return {"updated": IncidentCaseMemory().update_category(case_id, payload.category)}


@router.delete("/incidents/{case_id}")
async def delete_incident_case(case_id: str):
    return {"deleted": IncidentCaseMemory().delete_case(case_id)}
