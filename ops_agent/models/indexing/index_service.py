"""Index status and rebuild operations."""
from pathlib import Path
from typing import Any


class IndexService:
    """Coordinates status and rebuild operations for local indexes."""

    def status(self) -> dict[str, Any]:
        from config.settings import settings, PROJECT_ROOT
        from ops_agent.data.vector_store import VectorStore

        collections = []
        for name in [
            settings.milvus_knowledge_collection,
            settings.milvus_logs_collection,
            "ops_incident_cases",
        ]:
            try:
                store = VectorStore(name)
                count = store.count()
                state = "ready"
            except Exception as e:
                count = 0
                state = f"error: {e}"
            collections.append({"name": name, "count": count, "status": state})

        return {
            "milvus_db_path": settings.milvus_db_path,
            "knowledge_dir": str(PROJECT_ROOT / "data" / "knowledge"),
            "log_dir": str(PROJECT_ROOT / "data" / "logs"),
            "collections": collections,
        }

    def rebuild_knowledge(self) -> dict[str, Any]:
        from config.settings import PROJECT_ROOT
        from ops_agent.models.knowledge.knowledge_service import KnowledgeService

        return KnowledgeService(PROJECT_ROOT / "data" / "knowledge").rebuild_index()

    def rebuild_logs(self, path: str | None = None) -> dict[str, Any]:
        from config.settings import PROJECT_ROOT, settings
        from ops_agent.models.rag.log_parser import LogIndexer

        target = Path(path) if path else PROJECT_ROOT / "data" / "logs"
        indexer = LogIndexer()
        indexer.build_index(str(target))
        return {
            "status": "completed",
            "collection": settings.milvus_logs_collection,
            "target": str(target),
            "count": indexer.store.count(),
        }

    def clear_collection(self, collection: str) -> dict[str, Any]:
        from ops_agent.data.vector_store import VectorStore

        store = VectorStore(collection)
        store.clear()
        return {"status": "cleared", "collection": collection}
