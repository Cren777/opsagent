"""Log and incident case management routes."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ops_agent.models.troubleshooting.case_memory import IncidentCaseMemory
from ops_agent.models.uploads.log_upload_service import LogUploadService

router = APIRouter(prefix="/api", tags=["日志与案例"])


class CaseStatusUpdate(BaseModel):
    status: str


@router.get("/logs")
async def list_uploaded_logs():
    return LogUploadService().list_logs()


@router.get("/logs/{file_id}")
async def get_uploaded_log(file_id: str):
    metadata = LogUploadService().get_metadata(file_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="日志不存在")
    return metadata


@router.delete("/logs/{file_id}")
async def delete_uploaded_log(file_id: str):
    return {"deleted": LogUploadService().delete_log(file_id)}


@router.get("/incidents")
async def list_incident_cases(status: str | None = None):
    return IncidentCaseMemory().list_cases(status=status)


@router.get("/incidents/{case_id}")
async def get_incident_case(case_id: str):
    item = IncidentCaseMemory().get_case(case_id)
    if not item:
        raise HTTPException(status_code=404, detail="案例不存在")
    return item


@router.put("/incidents/{case_id}/status")
async def update_incident_status(case_id: str, payload: CaseStatusUpdate):
    return {"updated": IncidentCaseMemory().update_status(case_id, payload.status)}


@router.delete("/incidents/{case_id}")
async def delete_incident_case(case_id: str):
    return {"deleted": IncidentCaseMemory().delete_case(case_id)}
