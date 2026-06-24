"""FastAPI 搴旂敤鍏ュ彛"""
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from ops_agent.api.routes import auth, chat, health, config, uploads, knowledge, incidents, diagnostics, indexes
from ops_agent.api.middleware.auth import APIKeyMiddleware
from ops_agent.api.dependencies.auth import get_current_user
from ops_agent.utils.logging_config import setup_logging
from config.settings import settings
from ops_agent.api.services.config_service import seed_default_configs


setup_logging()

# 鍚姩鏃跺垵濮嬪寲閰嶇疆鏁版嵁搴擄紙鍦ㄥ鍏ヨ矾鐢变箣鍓嶏紝纭繚 get_dynamic_llm_client 鑳借鍙栧埌閰嶇疆锛?
seed_default_configs()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """搴旂敤鐢熷懡鍛ㄦ湡绠＄悊"""
    # 鍚姩鏃讹細鍦ㄥ悗鍙扮嚎绋嬮鍔犺浇 Embedding 妯″瀷
    import asyncio
    loop = asyncio.get_event_loop()

    def _load_embedder():
        from ops_agent.models.embedding.embedder import get_embedder
        emb = get_embedder()
        _ = emb.dim
        logger.info("Embedding 妯″瀷棰勫姞杞藉畬鎴?)

    loop.run_in_executor(None, _load_embedder)
    yield


app = FastAPI(
    title="OpsAgent - 浼佷笟IT杩愮淮鍐呴儴瀹㈡湇",
    description="鍩轰簬澶фā鍨嬬殑鏅鸿兘IT杩愮淮鍔╂墜",
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

# API Key 璁よ瘉锛堝彲閫夛紝璋冭瘯妯″紡涓嬪鏉惧鐞嗭級
if not settings.debug:
    app.add_middleware(APIKeyMiddleware)

# 娉ㄥ唽璺敱
app.include_router(health.router, tags=["绯荤粺"])
app.include_router(chat.router, prefix="/api", tags=["瀵硅瘽"])
app.include_router(config.router, tags=["閰嶇疆绠＄悊"])
app.include_router(uploads.router)
app.include_router(knowledge.router)
app.include_router(incidents.router)
app.include_router(diagnostics.router)
app.include_router(indexes.router)

# 闈欐€佹枃浠?
dist_dir = Path(__file__).parent / "static" / "dist"
if dist_dir.exists():
    app.mount("/assets", StaticFiles(directory=str(dist_dir / "assets")), name="assets")
    logger.info("Vue 鍓嶇宸叉寕杞? {}", dist_dir)
else:
    logger.warning("Vue dist 鐩綍涓嶅瓨鍦? {}", dist_dir)


@app.get("/{full_path:path}")
async def spa_fallback(full_path: str = ""):
    """SPA fallback 鈥?serve index.html for all non-API routes."""
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

