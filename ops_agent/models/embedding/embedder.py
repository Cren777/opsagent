"""BGE Embedding 模型封装"""
import os
from typing import List

# 必须在任何 import 之前设置环境变量，确保模型从镜像加载
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

from sentence_transformers import SentenceTransformer
from loguru import logger

from config.settings import settings

# BGE 查询指令前缀（提升检索效果）
_BGE_QUERY_PREFIX = "为这个句子生成表示以用于检索相关文章："


class Embedder:
    """BGE-large-zh-v1.5 嵌入模型封装"""

    def __init__(self):
        self.model_name = settings.embedding_model_name
        self.device = settings.embedding_device
        self._model: SentenceTransformer | None = None
        logger.info("Embedder 初始化，模型: {} (设备: {})", self.model_name, self.device)

    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            self._model = SentenceTransformer(
                self.model_name,
                device=self.device,
            )
            logger.info("Embedding 模型已加载: {} -> {}d", self.model_name, self._model.get_sentence_embedding_dimension())
        return self._model

    def encode(self, text: str, is_query: bool = False) -> List[float]:
        """编码单条文本为向量

        Args:
            text: 输入文本
            is_query: 是否为查询文本（True时添加查询前缀）
        """
        if is_query:
            text = _BGE_QUERY_PREFIX + text
        embedding = self.model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    def encode_batch(self, texts: List[str]) -> List[List[float]]:
        """批量编码文本"""
        embeddings = self.model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return embeddings.tolist()

    @property
    def dim(self) -> int:
        return self.model.get_sentence_embedding_dimension()


# 全局单例
_embedder: Embedder | None = None


def get_embedder() -> Embedder:
    global _embedder
    if _embedder is None:
        _embedder = Embedder()
    return _embedder
