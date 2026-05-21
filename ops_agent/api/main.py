"""FastAPI 应用入口"""
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from ops_agent.api.routes import chat, health, config
from ops_agent.api.middleware.auth import APIKeyMiddleware
from ops_agent.utils.logging_config import setup_logging
from config.settings import settings
from ops_agent.api.services.config_service import seed_default_configs


setup_logging()

# 启动时初始化配置数据库（在导入路由之前，确保 get_dynamic_llm_client 能读取到配置）
seed_default_configs()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时：在后台线程预加载 Embedding 模型
    import asyncio
    loop = asyncio.get_event_loop()

    def _load_embedder():
        from ops_agent.models.embedding.embedder import get_embedder
        emb = get_embedder()
        _ = emb.dim
        logger.info("Embedding 模型预加载完成")

    loop.run_in_executor(None, _load_embedder)
    yield


app = FastAPI(
    title="OpsAgent - 企业IT运维内部客服",
    description="基于大模型的智能IT运维助手",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Key 认证（可选，调试模式下宽松处理）
if not settings.debug:
    app.add_middleware(APIKeyMiddleware)

# 注册路由
app.include_router(health.router, tags=["系统"])
app.include_router(chat.router, prefix="/api", tags=["对话"])
app.include_router(config.router, tags=["配置管理"])

# 静态文件
dist_dir = Path(__file__).parent / "static" / "dist"
if dist_dir.exists():
    app.mount("/assets", StaticFiles(directory=str(dist_dir / "assets")), name="assets")
    logger.info("Vue 前端已挂载: {}", dist_dir)
else:
    logger.warning("Vue dist 目录不存在: {}", dist_dir)


@app.get("/{full_path:path}")
async def spa_fallback(full_path: str = ""):
    """SPA fallback — serve index.html for all non-API routes."""
    from fastapi.responses import HTMLResponse
    index_file = Path(__file__).parent / "static" / "dist" / "index.html"
    if index_file.exists():
        if full_path.startswith("api/") or full_path.startswith("health"):
            from fastapi.responses import JSONResponse
            return JSONResponse({"detail": "Not found"}, status_code=404)
        return HTMLResponse(index_file.read_text(encoding="utf-8"))
    return {"message": "OpsAgent API is running", "docs": "/docs"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "ops_agent.api.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
