"""Upload endpoints for troubleshooting artifacts."""
from fastapi import APIRouter, HTTPException, Query, Request
from loguru import logger

from ops_agent.models.uploads.log_upload_service import LogUploadService

router = APIRouter(prefix="/api/uploads", tags=["上传"])


@router.post("/logs")
async def upload_log(
    request: Request,
    filename: str = Query(default="uploaded.log", description="Original log filename"),
    category: str = Query(default="", description="Log category path"),
):
    """Upload a log file as raw request body and return its analysis metadata."""
    try:
        content = await request.body()
        if not content:
            raise HTTPException(status_code=400, detail="日志文件为空")
        return LogUploadService().save_log_file(filename, content, category=category)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("日志上传失败")
        raise HTTPException(status_code=500, detail=f"日志上传失败: {e}") from e
