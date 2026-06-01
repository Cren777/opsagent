"""Upload, discover, store, and summarize log files."""
import gzip
import hashlib
import json
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from ops_agent.models.category_registry import CategoryRegistry


_SECRET_PATTERNS = [
    re.compile(r"(?i)(password|passwd|pwd)\s*[:=]\s*[^\s,;]+"),
    re.compile(r"(?i)(token|secret|api[_-]?key)\s*[:=]\s*[^\s,;]+"),
    re.compile(r"(?i)(authorization:\s*bearer)\s+[^\s,;]+"),
]

_PATTERN_HINTS = [
    "Connection refused",
    "Permission denied",
    "Out of memory",
    "No space left",
    "disk full",
    "timeout",
    "timed out",
    "segmentation fault",
    "502",
    "503",
    "OOM",
]

_LOG_NAME_RE = re.compile(r"([A-Za-z0-9_.-]+\.(?:log|txt|out|gz))", re.IGNORECASE)


class LogUploadService:
    """Persists uploaded logs and exposes a unified catalog of local logs."""

    allowed_suffixes = {".log", ".txt", ".out", ".gz"}

    def __init__(
        self,
        base_dir: str | Path | None = None,
        max_bytes: int = 20 * 1024 * 1024,
        source_dirs: list[str | Path] | None = None,
    ):
        self.base_dir = Path(base_dir or self._default_base_dir())
        self.max_bytes = max_bytes
        self.source_dirs = [Path(path) for path in (source_dirs or self._default_source_dirs())]
        self.files_dir = self.base_dir / "files"
        self.meta_dir = self.base_dir / "metadata"
        self.category_registry = CategoryRegistry(self.base_dir / "categories.json")
        self.files_dir.mkdir(parents=True, exist_ok=True)
        self.meta_dir.mkdir(parents=True, exist_ok=True)

    def save_log_file(self, filename: str, content: bytes, category: str = "") -> dict[str, Any]:
        """Save a user-uploaded log file and return metadata plus a redacted summary."""
        safe_name = self._safe_filename(filename)
        suffix = Path(safe_name).suffix.lower()
        if suffix not in self.allowed_suffixes:
            raise ValueError(f"不支持的日志文件类型: {suffix or 'unknown'}")
        if len(content) > self.max_bytes:
            raise ValueError(f"日志文件过大，最大允许 {self.max_bytes // 1024 // 1024}MB")

        file_id = f"log_{uuid.uuid4().hex}"
        day_dir = self.files_dir / datetime.utcnow().strftime("%Y%m%d")
        day_dir.mkdir(parents=True, exist_ok=True)
        stored_path = day_dir / f"{file_id}_{safe_name}"
        stored_path.write_bytes(content)

        text = self._decode_content(safe_name, content)
        analysis = self.analyze_text(text)
        now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        metadata = {
            "file_id": file_id,
            "filename": safe_name,
            "size": len(content),
            "category": self._safe_category(category) if category else self._auto_category(safe_name, text),
            "source": "uploaded",
            "severity": self._severity_from_analysis(analysis),
            "tags": analysis.get("patterns", []),
            "stored_path": str(stored_path),
            "uploaded_at": now,
            "updated_at": now,
            "mtime": stored_path.stat().st_mtime,
            "analysis": analysis,
        }
        self._write_metadata(metadata)
        return metadata

    def get_metadata(self, file_id: str) -> dict[str, Any] | None:
        meta_path = self.meta_dir / f"{file_id}.json"
        if meta_path.exists():
            return json.loads(meta_path.read_text(encoding="utf-8"))
        for item in self._discover_source_logs():
            if item.get("file_id") == file_id:
                return item
        return None

    def list_logs(
        self,
        query: str = "",
        category: str = "",
        source: str = "",
        severity: str = "",
    ) -> list[dict[str, Any]]:
        uploaded = self._list_uploaded_logs()
        discovered = self._discover_source_logs()
        merged = self._merge_by_identity(uploaded + discovered)
        filtered = self._filter_logs(merged, query=query, category=category, source=source, severity=severity)
        return sorted(filtered, key=lambda item: item.get("mtime", 0), reverse=True)

    def update_category(self, file_id: str, category: str) -> bool:
        metadata = self.get_metadata(file_id)
        if not metadata:
            return False
        metadata["category"] = self._safe_category(category)
        metadata["category_source"] = "manual"
        metadata["updated_at"] = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        self._write_metadata(metadata)
        return True

    def preview_log(self, file_id: str, max_chars: int = 5000) -> dict[str, Any]:
        metadata = self.get_metadata(file_id)
        if not metadata:
            raise FileNotFoundError(file_id)
        stored_path = Path(metadata.get("stored_path", ""))
        if not stored_path.exists() or not self._is_allowed_log_path(stored_path):
            raise FileNotFoundError(file_id)
        raw = self._read_path_bytes(stored_path)
        content = self._redact(self._decode_content(metadata.get("filename", stored_path.name), raw))
        return {**metadata, "content": content[:max_chars]}

    def delete_log(self, file_id: str) -> bool:
        metadata = self.get_metadata(file_id)
        if not metadata:
            return False

        stored_path = Path(metadata.get("stored_path", ""))
        if metadata.get("source") == "uploaded":
            try:
                if stored_path.exists() and stored_path.resolve().is_relative_to(self.files_dir.resolve()):
                    stored_path.unlink()
            except OSError:
                pass

        meta_path = self.meta_dir / f"{file_id}.json"
        if meta_path.exists():
            meta_path.unlink()
        return True

    def get_attachment_context(self, attachments: list[dict[str, Any]] | None) -> str:
        """Render log analyses as prompt context."""
        if not attachments:
            return ""

        blocks: list[str] = []
        for attachment in attachments:
            if attachment.get("type") != "log":
                continue
            file_id = str(attachment.get("id") or "")
            metadata = self.get_metadata(file_id)
            if not metadata:
                blocks.append(f"[日志缺失] {file_id}")
                continue
            analysis = metadata.get("analysis", {})
            blocks.append(
                "\n".join(
                    [
                        f"[日志] {metadata.get('filename', file_id)}",
                        f"来源: {metadata.get('source', 'unknown')}，分类: {metadata.get('category', '未分类')}",
                        f"错误数: {analysis.get('error_count', 0)}，警告数: {analysis.get('warning_count', 0)}",
                        f"关键模式: {', '.join(analysis.get('patterns', [])) or '未识别'}",
                        "关键片段:",
                        str(analysis.get("summary", "")),
                    ]
                )
            )
        return "\n\n".join(blocks)

    def resolve_mentioned_logs(self, query: str, limit: int = 3) -> list[dict[str, Any]]:
        wanted = {Path(match.group(1)).name.lower() for match in _LOG_NAME_RE.finditer(query)}
        if not wanted:
            return []

        matches = []
        for item in self.list_logs():
            if item.get("filename", "").lower() in wanted:
                matches.append({
                    "id": item["file_id"],
                    "type": "log",
                    "filename": item["filename"],
                    "source": item.get("source", ""),
                    "size": item.get("size", 0),
                })
        return matches[:limit]

    def iter_indexable_paths(self) -> list[Path]:
        paths = []
        for item in self.list_logs():
            path = Path(item.get("stored_path", ""))
            if path.exists() and self._is_allowed_log_path(path):
                paths.append(path)
        return paths

    def category_summary(self) -> list[dict[str, Any]]:
        groups: dict[str, dict[str, Any]] = {}
        for item in self.list_logs():
            name = item.get("category") or "未分类"
            analysis = item.get("analysis", {})
            group = groups.setdefault(name, {
                "name": name,
                "count": 0,
                "error_count": 0,
                "warning_count": 0,
            })
            group["count"] += 1
            group["error_count"] += int(analysis.get("error_count", 0))
            group["warning_count"] += int(analysis.get("warning_count", 0))
        for item in self.category_registry.list_categories():
            group = groups.setdefault(item["name"], {
                "name": item["name"],
                "count": 0,
                "error_count": 0,
                "warning_count": 0,
            })
            group["pinned"] = item.get("pinned", False)
            group["user_defined"] = True
        for group in groups.values():
            group.setdefault("pinned", False)
            group.setdefault("user_defined", False)
        return sorted(groups.values(), key=lambda item: (not item.get("pinned", False), -item["count"], item["name"]))

    def create_category(self, name: str) -> dict[str, Any]:
        return self.category_registry.create(name)

    def rename_category(self, old_name: str, new_name: str) -> dict[str, Any]:
        old_safe = self._safe_category(old_name)
        item = self.category_registry.rename(old_safe, new_name)
        for log in self.list_logs(category=old_safe):
            self.update_category(log["file_id"], item["name"])
        return item

    def set_category_pinned(self, name: str, pinned: bool) -> dict[str, Any]:
        return self.category_registry.set_pinned(name, pinned)

    def delete_category(self, name: str) -> bool:
        safe_name = self._safe_category(name)
        deleted = self.category_registry.delete(safe_name)
        for log in self.list_logs(category=safe_name):
            self.update_category(log["file_id"], "")
        return deleted

    @classmethod
    def analyze_text(cls, text: str) -> dict[str, Any]:
        redacted = cls._redact(text)
        lines = [line.strip() for line in redacted.splitlines() if line.strip()]
        error_lines = [line for line in lines if re.search(r"(?i)\berror\b|fatal|crit|\[error\]", line)]
        warning_lines = [line for line in lines if re.search(r"(?i)\bwarn(?:ing)?\b|\[warn\]", line)]
        selected = (error_lines + warning_lines + lines[:5])[:20]
        patterns = cls._detect_patterns(redacted)
        return {
            "line_count": len(lines),
            "error_count": len(error_lines),
            "warning_count": len(warning_lines),
            "patterns": patterns,
            "summary": "\n".join(selected)[:5000],
        }

    def _list_uploaded_logs(self) -> list[dict[str, Any]]:
        logs = []
        for meta_path in sorted(self.meta_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            metadata = json.loads(meta_path.read_text(encoding="utf-8"))
            if metadata.get("source") not in ("", "uploaded") and not metadata.get("file_id", "").startswith("log_"):
                continue
            logs.append(self._normalize_metadata(metadata))
        return logs

    def _discover_source_logs(self) -> list[dict[str, Any]]:
        items = []
        for index, root in enumerate(self.source_dirs):
            if not root.exists():
                continue
            source = self._source_label(root, index)
            for path in root.rglob("*"):
                if path.is_file() and path.suffix.lower() in self.allowed_suffixes:
                    items.append(self._metadata_from_existing_file(path, source))
        return items

    def _metadata_from_existing_file(self, path: Path, source: str) -> dict[str, Any]:
        resolved = path.resolve()
        file_id = self._local_file_id(resolved)
        override = self._read_metadata(file_id) or {}
        raw = self._read_path_bytes(resolved)
        text = self._decode_content(resolved.name, raw)
        analysis = self.analyze_text(text)
        stat = resolved.stat()
        category = override.get("category") or self._auto_category(resolved.name, text)
        return self._normalize_metadata({
            **override,
            "file_id": file_id,
            "filename": resolved.name,
            "size": stat.st_size,
            "category": category,
            "source": source,
            "severity": self._severity_from_analysis(analysis),
            "tags": analysis.get("patterns", []),
            "stored_path": str(resolved),
            "uploaded_at": override.get("uploaded_at") or datetime.utcfromtimestamp(stat.st_mtime).isoformat(timespec="seconds") + "Z",
            "updated_at": override.get("updated_at") or datetime.utcfromtimestamp(stat.st_mtime).isoformat(timespec="seconds") + "Z",
            "mtime": stat.st_mtime,
            "analysis": analysis,
        })

    def _filter_logs(
        self,
        logs: list[dict[str, Any]],
        query: str = "",
        category: str = "",
        source: str = "",
        severity: str = "",
    ) -> list[dict[str, Any]]:
        query_lower = query.strip().lower()
        result = []
        for item in logs:
            if query_lower:
                haystack = " ".join([
                    item.get("filename", ""),
                    item.get("category", ""),
                    " ".join(item.get("tags", [])),
                    item.get("analysis", {}).get("summary", ""),
                ]).lower()
                if query_lower not in haystack:
                    continue
            if category and item.get("category") != category:
                continue
            if source and item.get("source") != source:
                continue
            if severity and item.get("severity") != severity:
                continue
            result.append(item)
        return result

    def _merge_by_identity(self, logs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        merged: dict[str, dict[str, Any]] = {}
        for item in logs:
            merged[item["file_id"]] = item
        return list(merged.values())

    def _normalize_metadata(self, metadata: dict[str, Any]) -> dict[str, Any]:
        analysis = metadata.get("analysis") or {}
        metadata.setdefault("category", "")
        metadata.setdefault("source", "uploaded")
        metadata.setdefault("severity", self._severity_from_analysis(analysis))
        metadata.setdefault("tags", analysis.get("patterns", []))
        metadata.setdefault("updated_at", metadata.get("uploaded_at", ""))
        metadata.setdefault("mtime", 0)
        return metadata

    def _write_metadata(self, metadata: dict[str, Any]) -> None:
        self.meta_dir.mkdir(parents=True, exist_ok=True)
        (self.meta_dir / f"{metadata['file_id']}.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _read_metadata(self, file_id: str) -> dict[str, Any] | None:
        meta_path = self.meta_dir / f"{file_id}.json"
        if not meta_path.exists():
            return None
        return json.loads(meta_path.read_text(encoding="utf-8"))

    def _read_path_bytes(self, path: Path) -> bytes:
        with path.open("rb") as handle:
            return handle.read(self.max_bytes)

    def _is_allowed_log_path(self, path: Path) -> bool:
        try:
            resolved = path.resolve()
            roots = [self.files_dir.resolve(), *[root.resolve() for root in self.source_dirs if root.exists()]]
            return any(resolved.is_relative_to(root) for root in roots)
        except OSError:
            return False

    def _source_label(self, root: Path, index: int) -> str:
        try:
            from config.settings import settings

            resolved = root.resolve()
            if resolved == Path(settings.runtime_logs_dir).resolve():
                return "runtime"
            if resolved == Path(settings.seed_logs_dir).resolve():
                return "seed"
        except Exception:
            pass
        return "runtime" if index == 0 else "seed" if index == 1 else "local"

    @staticmethod
    def _safe_filename(filename: str) -> str:
        name = Path(filename or "uploaded.log").name
        return re.sub(r"[^A-Za-z0-9._-]+", "_", name)[:160] or "uploaded.log"

    @staticmethod
    def _safe_category(category: str) -> str:
        normalized = str(category or "").replace("\\", "/").strip("/")
        if ".." in Path(normalized).parts:
            raise ValueError("非法的分类路径")
        parts = [re.sub(r"[^A-Za-z0-9._\-\u4e00-\u9fff]+", "_", part) for part in normalized.split("/") if part]
        return "/".join(parts)

    @staticmethod
    def _decode_content(filename: str, content: bytes) -> str:
        if filename.lower().endswith(".gz"):
            try:
                content = gzip.decompress(content)
            except OSError:
                pass
        return content.decode("utf-8", errors="ignore")

    @staticmethod
    def _redact(text: str) -> str:
        redacted = text
        for pattern in _SECRET_PATTERNS:
            redacted = pattern.sub(lambda m: f"{m.group(1)}=<redacted>", redacted)
        return redacted

    @staticmethod
    def _detect_patterns(text: str) -> list[str]:
        found = []
        lower = text.lower()
        for hint in _PATTERN_HINTS:
            if hint.lower() in lower:
                found.append(hint)
        return found

    @staticmethod
    def _severity_from_analysis(analysis: dict[str, Any]) -> str:
        if analysis.get("error_count", 0):
            return "error"
        if analysis.get("warning_count", 0):
            return "warning"
        return "info"

    @staticmethod
    def _auto_category(filename: str, text: str) -> str:
        lower_name = filename.lower()
        text_lower = text.lower()
        if lower_name.startswith("ops_agent_"):
            return "OpsAgent/运行日志"
        if "nginx" in lower_name or "access.log" in lower_name or "error.log" in lower_name:
            return "Nginx"
        if "mysql" in lower_name or "mysql" in text_lower:
            return "MySQL"
        return ""

    @staticmethod
    def _local_file_id(path: Path) -> str:
        digest = hashlib.sha1(str(path).encode("utf-8")).hexdigest()[:24]
        return f"local_{digest}"

    @staticmethod
    def _default_base_dir() -> Path:
        from config.settings import settings

        return Path(settings.uploaded_logs_dir)

    @staticmethod
    def _default_source_dirs() -> list[Path]:
        try:
            from config.settings import settings

            return [Path(settings.runtime_logs_dir), Path(settings.seed_logs_dir)]
        except Exception:
            return []
