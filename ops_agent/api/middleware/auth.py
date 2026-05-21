"""API Key 认证中间件"""
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from config.settings import settings


class APIKeyMiddleware(BaseHTTPMiddleware):
    """简单的 API Key 认证"""

    async def dispatch(self, request: Request, call_next):
        # 跳过静态文件和健康检查
        path = request.url.path
        if path.startswith("/static") or path == "/health":
            return await call_next(request)

        # 跳过 OPTIONS 请求（CORS preflight）
        if request.method == "OPTIONS":
            return await call_next(request)

        api_key = request.headers.get("X-API-Key") or request.query_params.get("api_key")
        if api_key != settings.api_key:
            raise HTTPException(status_code=401, detail="无效的 API Key")

        return await call_next(request)
