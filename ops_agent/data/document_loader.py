"""运维文档加载器：Markdown 文档分块"""
import re
from pathlib import Path
from typing import List
from dataclasses import dataclass, field
from loguru import logger

from config.settings import settings


@dataclass
class Document:
    """文档块"""
    content: str
    metadata: dict = field(default_factory=dict)


@dataclass
class DocumentChunk:
    """分块后的文档"""
    chunk_id: str
    content: str
    source_file: str
    title: str = ""
    chunk_index: int = 0


class DocumentLoader:
    """加载并分块 Markdown 文档"""

    def __init__(
        self,
        chunk_size: int = settings.rag_chunk_size,
        chunk_overlap: int = settings.rag_chunk_overlap,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def load_directory(self, dir_path: str) -> List[Document]:
        """加载目录下所有 Markdown 文件"""
        docs = []
        md_files = sorted(Path(dir_path).rglob("*.md"))
        logger.info("发现 {} 个 Markdown 文件", len(md_files))
        for md_file in md_files:
            docs.extend(self._load_file(md_file))
        return docs

    def _load_file(self, file_path: Path) -> List[Document]:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        # 提取标题（第一个 # 标题）
        title_match = re.search(r"^#\s+(.+)", content, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else file_path.stem
        return [Document(content=content, metadata={"source": str(file_path), "title": title})]

    def chunk_documents(self, documents: List[Document]) -> List[DocumentChunk]:
        """对文档进行分块"""
        chunks = []
        for doc in documents:
            source = doc.metadata.get("source", "")
            title = doc.metadata.get("title", "")

            # 按 Markdown 二级标题分节
            sections = self._split_by_headers(doc.content)

            chunk_idx = 0
            for section_title, section_text in sections:
                # 对每节按字数进一步分块
                sub_chunks = self._text_split(section_text)
                for sub_content in sub_chunks:
                    chapter = section_title or title
                    content_with_ctx = f"# {chapter}\n\n{sub_content.strip()}"
                    chunks.append(DocumentChunk(
                        chunk_id=f"{Path(source).stem}_{chunk_idx}",
                        content=content_with_ctx,
                        source_file=source,
                        title=title,
                        chunk_index=chunk_idx,
                    ))
                    chunk_idx += 1

        logger.info("文档分块完成: {} 个文档 → {} 个块", len(documents), len(chunks))
        return chunks

    def _split_by_headers(self, text: str) -> List[tuple]:
        """按 ## 或 ### 标题分节，返回 [(标题, 内容), ...]"""
        sections = []
        # 按 ## 分割
        parts = re.split(r"\n(?=## )", text)
        for part in parts:
            lines = part.strip().split("\n", 1)
            if len(lines) >= 1:
                header = lines[0].replace("#", "").strip()
                body = lines[1].strip() if len(lines) > 1 else ""
                sections.append((header, body))
        if not sections:
            sections.append(("", text))
        return sections

    def _text_split(self, text: str) -> List[str]:
        """按 chunk_size 字数分块（简单按字符数分割）"""
        if len(text) <= self.chunk_size:
            return [text] if text.strip() else []

        chunks = []
        start = 0
        while start < len(text):
            end = start + self.chunk_size
            # 尝试在换行处断开
            if end < len(text):
                nl = text.rfind("\n", start, end)
                if nl > start + self.chunk_size // 2:
                    end = nl + 1
            chunks.append(text[start:end])
            start = end - self.chunk_overlap
        return chunks
