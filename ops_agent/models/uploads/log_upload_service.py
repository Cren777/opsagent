"""Upload, store, and summarize user-provided log files."""
import gzip
import json
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any


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


class LogUploadService:
    """Persists uploaded logs and stores a compact, redacted analysis."""

    allowed_suffixes = {".log", ".txt", ".out", ".gz"}

    def __init__(self, base_dir: str | Path | None = None, max_bytes: int = 20 * 1024 * 1024):
        self.base_dir = Path(base_dir or self._default_base_dir())
        self.max_bytes = max_bytes
        self.files_dir = self.base_dir / "files"
        self.meta_dir = self.base_dir / "metadata"
        self.files_dir.mkdir(parents=True, exist_ok=True)
        self.meta_dir.mkdir(parents=True, exist_ok=True)

    def save_log_file(self, filename: str, content: bytes) -> dict[str, Any]:
        """Save a log file and return metadata plus a redacted summary."""
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
        metadata = {
            "file_id": file_id,
            "filename": safe_name,
            "size": len(content),
            "stored_path": str(stored_path),
            "uploaded_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "analysis": analysis,
        }
        (self.meta_dir / f"{file_id}.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return metadata

    def get_metadata(self, file_id: str) -> dict[str, Any] | None:
        meta_path = self.meta_dir / f"{file_id}.json"
        if not meta_path.exists():
            return None
        return json.loads(meta_path.read_text(encoding="utf-8"))

    def list_logs(self) -> list[dict[str, Any]]:
        logs = []
        for meta_path in sorted(self.meta_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            logs.append(json.loads(meta_path.read_text(encoding="utf-8")))
        return logs

    def delete_log(self, file_id: str) -> bool:
        metadata = self.get_metadata(file_id)
        if not metadata:
            return False
        stored_path = Path(metadata.get("stored_path", ""))
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
        """Render uploaded log analyses as prompt context."""
        if not attachments:
            return ""

        blocks: list[str] = []
        for attachment in attachments:
            if attachment.get("type") != "log":
                continue
            file_id = str(attachment.get("id") or "")
            metadata = self.get_metadata(file_id)
            if not metadata:
                blocks.append(f"[上传日志缺失] {file_id}")
                continue
            analysis = metadata.get("analysis", {})
            blocks.append(
                "\n".join(
                    [
                        f"[上传日志] {metadata.get('filename', file_id)}",
                        f"错误数: {analysis.get('error_count', 0)}，警告数: {analysis.get('warning_count', 0)}",
                        f"关键模式: {', '.join(analysis.get('patterns', [])) or '未识别'}",
                        "关键片段:",
                        str(analysis.get("summary", "")),
                    ]
                )
            )
        return "\n\n".join(blocks)

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

    @staticmethod
    def _safe_filename(filename: str) -> str:
        name = Path(filename or "uploaded.log").name
        return re.sub(r"[^A-Za-z0-9._-]+", "_", name)[:160] or "uploaded.log"

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
    def _default_base_dir() -> Path:
        from config.settings import settings

        return Path(settings.uploaded_logs_dir)
