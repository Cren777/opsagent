"""File-backed knowledge document management."""
import base64
import json
import re
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Any


class KnowledgeService:
    """Manages user knowledge files under data/knowledge."""

    allowed_suffixes = {".md", ".txt"}
    index_status_filename = ".index_status.json"

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

    def get_tree(self) -> list[dict[str, Any]]:
        root: dict[str, Any] = {"name": "", "relative_path": "", "children": [], "files": []}
        folder_map: dict[str, dict[str, Any]] = {"": root}

        for directory in sorted([p for p in self.base_dir.rglob("*") if p.is_dir()]):
            relative = directory.relative_to(self.base_dir).as_posix()
            node = folder_map.setdefault(relative, {
                "name": directory.name,
                "relative_path": relative,
                "children": [],
                "files": [],
            })
            parent_relative = directory.parent.relative_to(self.base_dir).as_posix() if directory.parent != self.base_dir else ""
            parent = folder_map.setdefault(parent_relative, {
                "name": directory.parent.name,
                "relative_path": parent_relative,
                "children": [],
                "files": [],
            })
            if node not in parent["children"]:
                parent["children"].append(node)

        for file in self.list_files():
            parent_relative = str(Path(file["relative_path"]).parent).replace("\\", "/")
            if parent_relative == ".":
                parent_relative = ""
            parent = folder_map.setdefault(parent_relative, {
                "name": Path(parent_relative).name if parent_relative else "",
                "relative_path": parent_relative,
                "children": [],
                "files": [],
            })
            parent["files"].append(file)

        return root["children"]

    def create_folder(self, folder_path: str) -> dict[str, Any]:
        relative = self._safe_relative_path(folder_path)
        target = self.base_dir / relative
        self._ensure_inside_base(target)
        target.mkdir(parents=True, exist_ok=True)
        return {"name": target.name, "relative_path": target.relative_to(self.base_dir).as_posix()}

    def rename_folder(self, folder_path: str, new_name: str) -> dict[str, Any]:
        relative = self._safe_relative_path(folder_path)
        target = self.base_dir / relative
        self._ensure_inside_base(target)
        if not target.exists() or not target.is_dir():
            raise FileNotFoundError(folder_path)

        safe_name = self._safe_folder_name(new_name)
        renamed = target.parent / safe_name
        self._ensure_inside_base(renamed)
        if renamed.exists():
            raise ValueError("目标文件夹已存在")

        target.rename(renamed)
        return {"name": renamed.name, "relative_path": renamed.relative_to(self.base_dir).as_posix()}

    def delete_folder(self, folder_path: str, recursive: bool = False) -> bool:
        relative = self._safe_relative_path(folder_path)
        target = self.base_dir / relative
        self._ensure_inside_base(target)
        if not target.exists() or not target.is_dir():
            return False
        if any(target.iterdir()):
            if not recursive:
                raise ValueError("文件夹非空，不能删除")
            shutil.rmtree(target)
            return True
        target.rmdir()
        return True

    def save_file(self, filename: str, content: bytes) -> dict[str, Any]:
        relative = self._safe_relative_path(filename)
        if relative.suffix.lower() not in self.allowed_suffixes:
            raise ValueError(f"不支持的知识文件类型: {relative.suffix or 'unknown'}")

        target = self.base_dir / relative
        self._ensure_inside_base(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return self._metadata(target)

    def save_file_to_folder(self, folder_path: str, filename: str, content: bytes) -> dict[str, Any]:
        folder = self._safe_relative_path(folder_path) if folder_path else Path()
        safe_name = self._safe_relative_path(filename).name
        return self.save_file((folder / safe_name).as_posix(), content)

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
        status = self.mark_indexed()
        return {
            "status": "completed",
            "collection": kb.store.collection_name,
            "count": kb.store.count(),
            "indexed_at": status["indexed_at"],
        }

    def mark_indexed(self) -> dict[str, Any]:
        indexed_timestamp = time.time()
        indexed_at = datetime.fromtimestamp(indexed_timestamp).isoformat(timespec="seconds")
        status = {"indexed_at": indexed_at, "indexed_timestamp": indexed_timestamp}
        self._index_status_path().write_text(json.dumps(status, ensure_ascii=False), encoding="utf-8")
        return status

    def _metadata(self, path: Path) -> dict[str, Any]:
        stat = path.stat()
        relative = path.relative_to(self.base_dir).as_posix()
        return {
            "file_id": self._id_from_relative(relative),
            "filename": path.name,
            "relative_path": relative,
            "size": stat.st_size,
            "updated_at": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
            "indexed": stat.st_mtime <= self._indexed_timestamp(),
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

    def _safe_folder_name(self, folder_name: str) -> str:
        safe = self._safe_relative_path(folder_name).name
        if not safe:
            raise ValueError("非法的知识文件夹名称")
        return safe

    def _ensure_inside_base(self, path: Path) -> None:
        if not path.resolve().is_relative_to(self.base_dir.resolve()):
            raise ValueError("非法的知识文件路径")

    def _index_status_path(self) -> Path:
        return self.base_dir / self.index_status_filename

    def _indexed_timestamp(self) -> float:
        path = self._index_status_path()
        if not path.exists():
            return 0
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return float(data.get("indexed_timestamp") or 0)
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return 0

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
