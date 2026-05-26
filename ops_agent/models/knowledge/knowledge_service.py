"""File-backed knowledge document management."""
import base64
import re
from datetime import datetime
from pathlib import Path
from typing import Any


class KnowledgeService:
    """Manages user knowledge files under data/knowledge."""

    allowed_suffixes = {".md", ".txt"}

    def __init__(self, base_dir: str | Path | None = None):
        self.base_dir = Path(base_dir or self._default_base_dir())
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def list_files(self) -> list[dict[str, Any]]:
        files = []
        for path in sorted(self.base_dir.rglob("*")):
            if not path.is_file() or path.name == "__init__.py":
                continue
            if path.suffix.lower() not in self.allowed_suffixes:
                continue
            files.append(self._metadata(path))
        return files

    def save_file(self, filename: str, content: bytes) -> dict[str, Any]:
        relative = self._safe_relative_path(filename)
        if relative.suffix.lower() not in self.allowed_suffixes:
            raise ValueError(f"不支持的知识文件类型: {relative.suffix or 'unknown'}")

        target = self.base_dir / relative
        self._ensure_inside_base(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return self._metadata(target)

    def get_file(self, file_id: str) -> dict[str, Any]:
        path = self._path_from_id(file_id)
        metadata = self._metadata(path)
        metadata["content"] = path.read_text(encoding="utf-8", errors="ignore")
        return metadata

    def delete_file(self, file_id: str) -> bool:
        path = self._path_from_id(file_id)
        if not path.exists():
            return False
        path.unlink()
        return True

    def rebuild_index(self) -> dict[str, Any]:
        from ops_agent.models.rag.knowledge_base import KnowledgeBase

        kb = KnowledgeBase()
        kb.build(str(self.base_dir))
        return {"status": "completed", "collection": kb.store.collection_name, "count": kb.store.count()}

    def _metadata(self, path: Path) -> dict[str, Any]:
        stat = path.stat()
        relative = path.relative_to(self.base_dir).as_posix()
        return {
            "file_id": self._id_from_relative(relative),
            "filename": path.name,
            "relative_path": relative,
            "size": stat.st_size,
            "updated_at": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
            "indexed": False,
        }

    def _path_from_id(self, file_id: str) -> Path:
        relative = self._relative_from_id(file_id)
        path = self.base_dir / relative
        self._ensure_inside_base(path)
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(file_id)
        return path

    def _safe_relative_path(self, filename: str) -> Path:
        normalized = str(filename or "knowledge.md").replace("\\", "/").strip("/")
        if not normalized or ".." in Path(normalized).parts:
            raise ValueError("非法的知识文件路径")
        parts = [re.sub(r"[^A-Za-z0-9._\-\u4e00-\u9fff]+", "_", part) for part in normalized.split("/")]
        return Path(*[part for part in parts if part])

    def _ensure_inside_base(self, path: Path) -> None:
        if not path.resolve().is_relative_to(self.base_dir.resolve()):
            raise ValueError("非法的知识文件路径")

    @staticmethod
    def _id_from_relative(relative: str) -> str:
        encoded = base64.urlsafe_b64encode(relative.encode("utf-8")).decode("ascii")
        return encoded.rstrip("=")

    @staticmethod
    def _relative_from_id(file_id: str) -> Path:
        padding = "=" * (-len(file_id) % 4)
        decoded = base64.urlsafe_b64decode((file_id + padding).encode("ascii")).decode("utf-8")
        return Path(decoded)

    @staticmethod
    def _default_base_dir() -> Path:
        from config.settings import PROJECT_ROOT

        return PROJECT_ROOT / "data" / "knowledge"
