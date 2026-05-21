"""知识库管理：文档加载 → 分块 → Embedding → 存储"""
from typing import List, Dict, Any
from loguru import logger

from ops_agent.data.document_loader import DocumentLoader, DocumentChunk
from ops_agent.data.vector_store import VectorStore
from ops_agent.models.embedding.embedder import get_embedder
from ops_agent.models.rag.retriever import Retriever
from config.settings import settings


class KnowledgeBase:
    """运维知识库"""

    def __init__(self, vector_store: VectorStore | None = None):
        self.store = vector_store or VectorStore(settings.milvus_knowledge_collection)
        self.retriever = Retriever(self.store)
        self.loader = DocumentLoader()
        self.embedder = get_embedder()

    def build(self, docs_dir: str):
        """从文档目录构建知识库

        Args:
            docs_dir: 包含 Markdown 文件的目录路径
        """
        logger.info("开始构建知识库: {}", docs_dir)

        self.store.clear()

        documents = self.loader.load_directory(docs_dir)
        if not documents:
            logger.warning("未找到任何文档")
            return

        chunks = self.loader.chunk_documents(documents)
        logger.info("文档分块: {} 个块", len(chunks))

        texts = [c.content for c in chunks]
        logger.info("开始生成 Embedding（共 {} 条）...", len(texts))
        vectors = self.embedder.encode_batch(texts)
        logger.info("Embedding 生成完成")

        count = self.store.insert(vectors, chunks)
        logger.info("知识库构建完成，共 {} 条", count)

    def query(self, question: str, top_k: int | None = None) -> str:
        """查询知识库，返回上下文字符串"""
        return self.retriever.retrieve_context(question, top_k)

    def search(self, question: str, top_k: int | None = None) -> List[Dict[str, Any]]:
        """查询知识库，返回结构化结果"""
        return self.retriever.retrieve(question, top_k)


# 全局单例
_knowledge_base: KnowledgeBase | None = None


def get_knowledge_base() -> KnowledgeBase:
    global _knowledge_base
    if _knowledge_base is None:
        _knowledge_base = KnowledgeBase()
    return _knowledge_base
