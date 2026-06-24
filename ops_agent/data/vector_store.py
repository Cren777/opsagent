"""Milvus 向量存储封装"""
import os
from typing import List, Dict, Any
from pymilvus import MilvusClient, DataType
from loguru import logger

from config.settings import settings
from ops_agent.utils.exceptions import VectorStoreError


class VectorStore:
    """Milvus 向量存储（连接 Docker Milvus Standalone）"""

    def __init__(self, collection_name: str = settings.milvus_knowledge_collection):
        self.collection_name = collection_name
        self.dim = settings.embedding_dim
        self.db_path = settings.milvus_db_path

        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.client = MilvusClient(self.db_path)
        logger.info("Milvus Lite 已连接: {}", self.db_path)

        self._ensure_collection()

    def _ensure_collection(self):
        """确保 Collection 存在"""
        if self.client.has_collection(self.collection_name):
            logger.info("Collection '{}' 已存在", self.collection_name)
            self._load_collection()
            return

        schema = MilvusClient.create_schema(
            auto_id=True,
            enable_dynamic_field=True,
        )
        schema.add_field("id", DataType.INT64, is_primary=True)
        schema.add_field("vector", DataType.FLOAT_VECTOR, dim=self.dim)
        schema.add_field("content", DataType.VARCHAR, max_length=65535)
        schema.add_field("source_file", DataType.VARCHAR, max_length=512)
        schema.add_field("title", DataType.VARCHAR, max_length=256)
        schema.add_field("chunk_index", DataType.INT32)

        index_params = self.client.prepare_index_params()
        index_params.add_index(
            field_name="vector",
            index_type="IVF_FLAT",
            metric_type="IP",
            params={"nlist": 128},
        )

        self.client.create_collection(
            collection_name=self.collection_name,
            schema=schema,
            index_params=index_params,
        )
        self._load_collection()
        logger.info("Collection '{}' 创建成功，维度: {}", self.collection_name, self.dim)

    def _load_collection(self):
        """Ensure the collection is loaded before query/search operations."""
        self.client.load_collection(self.collection_name)

    def insert(self, vectors: List[List[float]], chunks: List) -> int:
        """批量插入向量和文档块

        Args:
            vectors: 向量列表
            chunks: DocumentChunk 列表

        Returns:
            插入行数
        """
        if not vectors:
            return 0

        data = []
        for i, (vec, chunk) in enumerate(zip(vectors, chunks)):
            data.append({
                "vector": vec,
                "content": chunk.content,
                "source_file": chunk.source_file,
                "title": chunk.title,
                "chunk_index": chunk.chunk_index,
            })

        result = self.client.insert(self.collection_name, data)
        count = result.get("insert_count", 0)
        logger.info("插入 {} 条向量到 '{}'", count, self.collection_name)
        return count

    def search(
        self,
        query_vector: List[float],
        top_k: int = 5,
        filter_expr: str | None = None,
    ) -> List[Dict[str, Any]]:
        """向量相似度检索

        Args:
            query_vector: 查询向量
            top_k: 返回结果数
            filter_expr: 过滤表达式

        Returns:
            检索结果列表，每条包含 content, source_file, title, score
        """
        self._load_collection()
        if not self._has_data():
            return []

        # 确保 Collection 已加载
        self._load_collection()

        results = self.client.search(
            collection_name=self.collection_name,
            data=[query_vector],
            limit=top_k,
            output_fields=["content", "source_file", "title", "chunk_index"],
            filter=filter_expr,
        )

        if not results or not results[0]:
            return []

        hits = []
        for hit in results[0]:
            entity = hit.get("entity", {})
            hits.append({
                "content": entity.get("content", ""),
                "source_file": entity.get("source_file", ""),
                "title": entity.get("title", ""),
                "score": hit.get("distance", 0),
            })
        return hits

    def _has_data(self) -> bool:
        """检查 Collection 是否有数据"""
        try:
            self._load_collection()
            results = self.client.query(
                collection_name=self.collection_name,
                filter="id > 0",
                limit=1,
                output_fields=["id"],
            )
            return len(results) > 0
        except Exception as e:
            logger.warning("Milvus collection '{}' data probe failed after load: {}", self.collection_name, e)
            return True  # 有异常时假定有数据，正常走 search 流程

    def clear(self):
        """清空 Collection"""
        if self.client.has_collection(self.collection_name):
            self.client.drop_collection(self.collection_name)
            logger.info("Collection '{}' 已删除", self.collection_name)
            self._ensure_collection()

    def count(self) -> int:
        """获取文档数量"""
        if not self.client.has_collection(self.collection_name):
            return 0
        stats = self.client.get_collection_stats(self.collection_name)
        return stats.get("row_count", 0)
