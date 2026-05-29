"""Service layer for approved diagnostic scripts."""
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


class DiagnosticService:
    """Lists and runs approved diagnostic scripts."""

    def __init__(
        self,
        approved_dir: str | Path | None = None,
        pending_dir: str | Path | None = None,
        disabled_dir: str | Path | None = None,
        timeout: int | None = None,
        max_output_chars: int | None = None,
    ):
        if approved_dir is None:
            from config.settings import settings

            approved_dir = settings.approved_scripts_dir
            scripts_root = Path(settings.approved_scripts_dir).parent
            pending_dir = pending_dir or scripts_root / "pending"
            disabled_dir = disabled_dir or scripts_root / "disabled"
            timeout = timeout or settings.script_timeout
            max_output_chars = max_output_chars or settings.script_output_max_chars
        self.approved_dir = Path(approved_dir)
        self.pending_dir = Path(pending_dir or self.approved_dir.parent / "pending")
        self.disabled_dir = Path(disabled_dir or self.approved_dir.parent / "disabled")
        self.timeout = timeout or 30
        self.max_output_chars = max_output_chars or 5000
        self.approved_dir.mkdir(parents=True, exist_ok=True)
        self.pending_dir.mkdir(parents=True, exist_ok=True)
        self.disabled_dir.mkdir(parents=True, exist_ok=True)

    def list_scripts(self) -> list[dict[str, Any]]:
        scripts = []
        for path in sorted(self.approved_dir.iterdir()):
            if not path.is_file() or path.name.startswith("__"):
                continue
            if path.suffix.lower() not in {".sh", ".py", ".cmd", ".bat"}:
                continue
            scripts.append({
                "name": path.name,
                "size": path.stat().st_size,
                "description": self._read_description(path),
                "timeout": self.timeout,
            })
        return scripts

    def list_pending_scripts(self) -> list[dict[str, Any]]:
        return self._list_scripts_in_dir(self.pending_dir)

    def upload_script(self, filename: str, content: bytes) -> dict[str, Any]:
        safe_name = self._safe_script_name(filename)
        if len(content) > 100 * 1024:
            raise ValueError("脚本文件过大，最大允许 100KB")
        target = self.pending_dir / safe_name
        self._ensure_inside(target, self.pending_dir)
        target.write_bytes(content)
        item = self._script_metadata(target)
        item["status"] = "pending"
        return item

    def enable_script(self, script_name: str) -> dict[str, Any]:
        safe_name = self._safe_script_name(script_name)
        source = self.pending_dir / safe_name
        if not source.exists():
            source = self.disabled_dir / safe_name
        if not source.exists():
            raise FileNotFoundError(script_name)
        shutil.move(str(source), str(self.approved_dir / safe_name))
        return {"name": safe_name, "status": "enabled"}

    def disable_script(self, script_name: str) -> dict[str, Any]:
        safe_name = self._safe_script_name(script_name)
        source = self.approved_dir / safe_name
        if not source.exists():
            raise FileNotFoundError(script_name)
        shutil.move(str(source), str(self.disabled_dir / safe_name))
        return {"name": safe_name, "status": "disabled"}

    def delete_script(self, script_name: str, status: str = "pending") -> bool:
        safe_name = self._safe_script_name(script_name)
        base = {"approved": self.approved_dir, "pending": self.pending_dir, "disabled": self.disabled_dir}.get(status, self.pending_dir)
        target = base / safe_name
        self._ensure_inside(target, base)
        if not target.exists():
            return False
        target.unlink()
        return True

    def preview_script(self, script_name: str, status: str = "approved") -> dict[str, Any]:
        safe_name = self._safe_script_name(script_name)
        base = {"approved": self.approved_dir, "pending": self.pending_dir, "disabled": self.disabled_dir}.get(status, self.approved_dir)
        path = base / safe_name
        self._ensure_inside(path, base)
        if not path.exists():
            raise FileNotFoundError(script_name)
        item = self._script_metadata(path)
        item["status"] = status
        item["content"] = path.read_text(encoding="utf-8", errors="ignore")[:10000]
        return item

    def run_script(self, script_name: str, args: list[str] | None = None) -> dict[str, str]:
        safe_name = self._safe_script_name(script_name)
        script_path = self.approved_dir / safe_name
        if not script_path.exists():
            raise FileNotFoundError(script_name)
        if not script_path.resolve().is_relative_to(self.approved_dir.resolve()):
            raise ValueError("脚本路径不合法")

        cmd = [str(script_path)] + (args or [])
        if script_path.suffix.lower() == ".py":
            cmd = [sys.executable, str(script_path)] + (args or [])
        elif os.name == "nt" and script_path.suffix.lower() == ".sh":
            cmd = ["bash", str(script_path)] + (args or [])

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=self.timeout,
            cwd=str(self.approved_dir),
        )
        return {
            "stdout": result.stdout[:self.max_output_chars],
            "stderr": result.stderr[:self.max_output_chars],
            "exit_code": str(result.returncode),
        }

    @staticmethod
    def _read_description(path: Path) -> str:
        try:
            for line in path.read_text(encoding="utf-8", errors="ignore").splitlines()[:5]:
                stripped = line.strip()
                if stripped.startswith("#") and not stripped.startswith("#!"):
                    return stripped.lstrip("#").strip()
        except OSError:
            pass
        return ""

    def _list_scripts_in_dir(self, directory: Path) -> list[dict[str, Any]]:
        scripts = []
        for path in sorted(directory.iterdir()):
            if path.is_file() and path.suffix.lower() in {".sh", ".py"}:
                scripts.append(self._script_metadata(path))
        return scripts

    def _script_metadata(self, path: Path) -> dict[str, Any]:
        return {
            "name": path.name,
            "size": path.stat().st_size,
            "description": self._read_description(path),
            "timeout": self.timeout,
        }

    @staticmethod
    def _safe_script_name(filename: str) -> str:
        name = Path(filename or "").name
        if not re.match(r"^check_[A-Za-z0-9_.-]+\.(sh|py)$", name):
            raise ValueError("脚本文件名必须匹配 check_*.sh 或 check_*.py")
        return name

    @staticmethod
    def _ensure_inside(path: Path, base: Path) -> None:
        if not path.resolve().is_relative_to(base.resolve()):
            raise ValueError("脚本路径不合法")
