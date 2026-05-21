"""RAG 检索器：Embedding → Milvus 检索 → 返回上下文"""
from typing import List, Dict, Any
from loguru import logger

from config.settings import settings
from ops_agent.data.vector_store import VectorStore
from ops_agent.models.embedding.embedder import get_embedder


class Retriever:
    """基于 Milvus 的 RAG 检索器"""

    def __init__(self, vector_store: VectorStore):
        self.store = vector_store
        self.embedder = get_embedder()
        self.top_k = settings.rag_top_k

    def retrieve(self, query: str, top_k: int | None = None) -> List[Dict[str, Any]]:
        """检索相关文档

        Args:
            query: 查询文本
            top_k: 返回结果数（默认使用配置值）

        Returns:
            检索结果，每条含 content, source_file, title, score
        """
        query_vec = self.embedder.encode(query, is_query=True)
        k = top_k or self.top_k
        results = self.store.search(query_vec, top_k=k)

        logger.info("检索完成: query='{}' → {} 条结果", query[:50], len(results))
        return results

    def retrieve_context(self, query: str, top_k: int | None = None) -> str:
        """检索并拼接为上下文字符串"""
        results = self.retrieve(query, top_k)
        if not results:
            return ""

        parts = []
        for i, r in enumerate(results, 1):
            parts.append(f"[来源 {i}: {r['title']}]\n{r['content']}")

        return "\n\n---\n\n".join(parts)
