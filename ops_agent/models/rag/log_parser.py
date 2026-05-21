"""系统日志解析器：结构化解析 → 分块 → 建立日志向量索引"""
import re
from pathlib import Path
from typing import List
from datetime import datetime
from dataclasses import dataclass, field
from loguru import logger

from ops_agent.data.vector_store import VectorStore
from ops_agent.models.embedding.embedder import get_embedder
from config.settings import settings


@dataclass
class LogEntry:
    """结构化日志条目"""
    timestamp: str
    hostname: str
    process: str
    pid: str
    level: str
    message: str

    def to_text(self) -> str:
        return f"[{self.timestamp}] {self.hostname} {self.process}[{self.pid}]: {self.level}: {self.message}"


@dataclass
class LogChunk:
    """日志块（时间窗口聚合）"""
    chunk_id: str
    entries: List[LogEntry]
    window_start: str = ""
    window_end: str = ""
    hostname: str = ""

    @property
    def content(self) -> str:
        return "\n".join(e.to_text() for e in self.entries)


class LogParser:
    """Syslog 日志解析器"""

    # 标准 syslog 格式: MMM DD HH:MM:SS hostname process[pid]: message
    _SYSLOG_RE = re.compile(
        r"^(\w{3}\s+\d+\s+\d{2}:\d{2}:\d{2})\s+(\S+)\s+(\S+?)(?:\[(\d+)\])?:\s*(.*)$"
    )

    _LEVEL_KEYWORDS = {
        "ERROR": ["error", "fail", "fatal", "killed"],
        "WARNING": ["warn", "warning"],
        "CRIT": ["crit", "critical", "fatal"],
        "INFO": ["info", "note", "notice"],
    }

    def parse_file(self, file_path: str) -> List[LogEntry]:
        """解析日志文件"""
        entries = []
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                entry = self._parse_line(line)
                if entry:
                    entries.append(entry)
        logger.info("解析日志完成: {} 条有效记录", len(entries))
        return entries

    def _parse_line(self, line: str) -> LogEntry | None:
        match = self._SYSLOG_RE.match(line)
        if not match:
            return LogEntry(
                timestamp="",
                hostname="",
                process="",
                pid="",
                level=self._detect_level(line),
                message=line.strip(),
            )

        return LogEntry(
            timestamp=match.group(1),
            hostname=match.group(2),
            process=match.group(3),
            pid=match.group(4) or "",
            level=self._detect_level(match.group(5)),
            message=match.group(5),
        )

    def _detect_level(self, text: str) -> str:
        text_upper = text.upper()
        for level, keywords in _LEVEL_KEYWORDS.items():
            for kw in keywords:
                if kw.upper() in text_upper:
                    return level
        return "INFO"

    def chunk_by_window(self, entries: List[LogEntry], window_size: int = 50) -> List[LogChunk]:
        """按固定行数窗口分块"""
        chunks = []
        for i in range(0, len(entries), window_size // 2):  # 重叠窗口
            window = entries[i:i + window_size]
            if len(window) < 5:
                continue
            hostnames = set(e.hostname for e in window if e.hostname)
            chunks.append(LogChunk(
                chunk_id=f"log_chunk_{i}",
                entries=window,
                window_start=window[0].timestamp,
                window_end=window[-1].timestamp,
                hostname=list(hostnames)[0] if hostnames else "",
            ))
        return chunks


class LogIndexer:
    """日志向量索引构建与检索"""

    def __init__(self):
        self.parser = LogParser()
        self.store = VectorStore(settings.milvus_logs_collection)
        self.embedder = get_embedder()

    def build_index(self, log_dir_or_file: str):
        """构建日志向量索引"""
        log_path = Path(log_dir_or_file)
        if log_path.is_dir():
            files = list(log_path.glob("*.log"))
        else:
            files = [log_path]

        all_entries = []
        for fp in files:
            all_entries.extend(self.parser.parse_file(str(fp)))

        chunks = self.parser.chunk_by_window(all_entries, window_size=50)
        logger.info("日志分块: {} 个条目 → {} 个窗口", len(all_entries), len(chunks))

        # 优先处理 ERROR/CRIT 块
        error_chunks = [c for c in chunks if any(
            e.level in ("ERROR", "CRIT") for e in c.entries
        )]
        normal_chunks = [c for c in chunks if c not in error_chunks]

        # NOTE: Milvus Lite 的 insert 需要使用与 collection schema 匹配的字段
        # 这里使用自定义 DocumentChunk-like 对象
        class _FakeChunk:
            def __init__(self, c: LogChunk):
                self.content = c.content[:65535]
                self.source_file = str(log_path)
                self.title = f"日志 - {c.hostname} ({c.window_start} ~ {c.window_end})"
                self.chunk_index = 0

        all_to_index = error_chunks + normal_chunks  # ERROR 优先
        texts = [c.content[:65535] for c in all_to_index]
        if texts:
            vectors = self.embedder.encode_batch(texts)
            fake_chunks = [_FakeChunk(c) for c in all_to_index]
            self.store.insert(vectors, fake_chunks)
            logger.info("日志索引构建完成: {} 条", len(texts))
        else:
            logger.warning("没有可索引的日志内容")

    def search(self, query: str, top_k: int = 5) -> list:
        """搜索相关日志"""
        query_vec = self.embedder.encode(query, is_query=True)
        return self.store.search(query_vec, top_k=top_k)

    def search_by_host(self, hostname: str, top_k: int = 10) -> list:
        """按主机名过滤搜索"""
        query_vec = self.embedder.encode(f"日志 {hostname}", is_query=True)
        return self.store.search(query_vec, top_k=top_k)
