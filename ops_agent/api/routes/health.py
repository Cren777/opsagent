"""健康检查接口"""
from fastapi import APIRouter
from ops_agent.models.tools.db_connector import get_db_connector
from ops_agent.data.vector_store import VectorStore
from config.settings import settings

router = APIRouter()


@router.get("/health")
async def health_check():
    db_ok = False
    try:
        db_ok = get_db_connector().health_check()
    except Exception:
        pass

    milvus_ok = False
    try:
        store = VectorStore(settings.milvus_knowledge_collection)
        count = store.count()
        milvus_ok = count >= 0
    except Exception:
        pass

    return {
        "status": "ok" if (db_ok) else "degraded",
        "database": "up" if db_ok else "down",
        "milvus": "up" if milvus_ok else "down",
    }
