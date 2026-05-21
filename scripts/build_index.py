#!/usr/bin/env python3
"""一键构建 Milvus 知识库向量索引"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import settings
from ops_agent.data.vector_store import VectorStore
from ops_agent.models.rag.knowledge_base import KnowledgeBase


def main():
    docs_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "knowledge"
    )

    print(f"文档目录: {docs_dir}")
    print(f"Milvus Lite 数据库: {settings.milvus_db_path}")

    kb = KnowledgeBase()
    kb.build(docs_dir)

    print(f"\n知识库构建完成！")
    print(f"  文档数: {kb.store.count()}")

    # 测试检索
    print("\n测试检索: '如何查看磁盘使用率？'")
    results = kb.search("如何查看磁盘使用率？", top_k=3)
    for i, r in enumerate(results, 1):
        print(f"  [{i}] {r['title']} (score: {r['score']:.4f})")
        print(f"      {r['content'][:100]}...")


if __name__ == "__main__":
    main()
