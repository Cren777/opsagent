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

    def rebuild_cases(self) -> dict[str, Any]:
        from ops_agent.data.vector_store import VectorStore
        from ops_agent.models.embedding.embedder import get_embedder
        from ops_agent.models.troubleshooting.case_memory import IncidentCaseMemory

        collection = "ops_incident_cases"
        store = VectorStore(collection)
        store.clear()
        cases = IncidentCaseMemory().list_cases(limit=1000)
        texts = [self._case_to_text(item) for item in cases]
        if not texts:
            return {"status": "completed", "collection": collection, "count": 0}

        class _CaseChunk:
            def __init__(self, case: dict[str, Any], content: str, index: int):
                self.content = content[:65535]
                self.source_file = case.get("case_id", "")
                self.title = case.get("query", "")[:256]
                self.chunk_index = index

        vectors = get_embedder().encode_batch(texts)
        chunks = [_CaseChunk(case, text, idx) for idx, (case, text) in enumerate(zip(cases, texts))]
        store.insert(vectors, chunks)
        return {"status": "completed", "collection": collection, "count": store.count()}

    def clear_collection(self, collection: str) -> dict[str, Any]:
        from ops_agent.data.vector_store import VectorStore

        store = VectorStore(collection)
        store.clear()
        return {"status": "cleared", "collection": collection}

    @staticmethod
    def _case_to_text(item: dict[str, Any]) -> str:
        return "\n".join([
            f"问题: {item.get('query', '')}",
            f"分类: {item.get('category', '')}",
            f"状态: {item.get('status', '')}",
            f"症状: {', '.join(item.get('symptoms', []))}",
            f"根因: {item.get('root_cause', '')}",
            f"解决方案: {item.get('solution', '')}",
            f"证据: {'; '.join(item.get('evidence', []))}",
            f"回答: {item.get('answer', '')}",
        ])
