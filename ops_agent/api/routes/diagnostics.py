"""Diagnostic tool management routes."""
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from ops_agent.models.tools.diagnostic_service import DiagnosticService

router = APIRouter(prefix="/api/diagnostics", tags=["诊断工具"])


class ScriptRunRequest(BaseModel):
    args: list[str] = []


@router.get("/scripts")
async def list_diagnostic_scripts():
    return DiagnosticService().list_scripts()


@router.get("/pending")
async def list_pending_diagnostic_scripts():
    return DiagnosticService().list_pending_scripts()


@router.post("/upload")
async def upload_diagnostic_script(
    request: Request,
    filename: str = Query(..., description="Script filename, must match check_*.sh or check_*.py"),
):
    try:
        return DiagnosticService().upload_script(filename, await request.body())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/scripts/{script_name}/preview")
async def preview_diagnostic_script(script_name: str, status: str = Query(default="approved")):
    try:
        return DiagnosticService().preview_script(script_name, status=status)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail="脚本不存在") from e


@router.post("/scripts/{script_name}/enable")
async def enable_diagnostic_script(script_name: str):
    try:
        return DiagnosticService().enable_script(script_name)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail="脚本不存在") from e


@router.post("/scripts/{script_name}/disable")
async def disable_diagnostic_script(script_name: str):
    try:
        return DiagnosticService().disable_script(script_name)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail="脚本不存在") from e


@router.delete("/scripts/{script_name}")
async def delete_diagnostic_script(script_name: str, status: str = Query(default="pending")):
    return {"deleted": DiagnosticService().delete_script(script_name, status=status)}


@router.post("/scripts/{script_name}/run")
async def run_diagnostic_script(script_name: str, payload: ScriptRunRequest):
    return DiagnosticService().run_script(script_name, args=payload.args)
