"""Diagnostic tool management routes."""
from fastapi import APIRouter
from pydantic import BaseModel

from ops_agent.models.tools.diagnostic_service import DiagnosticService

router = APIRouter(prefix="/api/diagnostics", tags=["诊断工具"])


class ScriptRunRequest(BaseModel):
    args: list[str] = []


@router.get("/scripts")
async def list_diagnostic_scripts():
    return DiagnosticService().list_scripts()


@router.post("/scripts/{script_name}/run")
async def run_diagnostic_script(script_name: str, payload: ScriptRunRequest):
    return DiagnosticService().run_script(script_name, args=payload.args)
