"""Service layer for approved diagnostic scripts."""
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


class DiagnosticService:
    """Lists and runs approved diagnostic scripts."""

    def __init__(
        self,
        approved_dir: str | Path | None = None,
        timeout: int | None = None,
        max_output_chars: int | None = None,
    ):
        if approved_dir is None:
            from config.settings import settings

            approved_dir = settings.approved_scripts_dir
            timeout = timeout or settings.script_timeout
            max_output_chars = max_output_chars or settings.script_output_max_chars
        self.approved_dir = Path(approved_dir)
        self.timeout = timeout or 30
        self.max_output_chars = max_output_chars or 5000

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

    def run_script(self, script_name: str, args: list[str] | None = None) -> dict[str, str]:
        script_path = self.approved_dir / script_name
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
