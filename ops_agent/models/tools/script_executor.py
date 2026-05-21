"""诊断脚本执行器（安全沙箱）"""
import os
import subprocess
from pathlib import Path
from typing import Dict
from loguru import logger

from config.settings import settings
from ops_agent.utils.exceptions import ScriptExecutionError, ScriptTimeoutError


class ScriptExecutor:
    """安全脚本执行器"""

    def __init__(self):
        self.approved_dir = Path(settings.approved_scripts_dir)
        self.timeout = settings.script_timeout
        self.max_output_chars = settings.script_output_max_chars

    def execute(self, script_name: str, args: list | None = None) -> Dict[str, str]:
        """执行预审批的诊断脚本

        Args:
            script_name: 脚本文件名（必须在 approved 目录下）
            args: 脚本参数列表

        Returns:
            {"stdout": "...", "stderr": "...", "exit_code": "0"}
        """
        script_path = self.approved_dir / script_name
        if not script_path.exists():
            raise ScriptExecutionError(f"脚本不存在: {script_name}")
        if not script_path.resolve().is_relative_to(self.approved_dir.resolve()):
            raise ScriptExecutionError(f"脚本路径不合法: {script_name}")

        cmd = [str(script_path)] + (args or [])
        logger.info("执行脚本: {}", " ".join(cmd))

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=str(self.approved_dir),
            )
        except subprocess.TimeoutExpired:
            raise ScriptTimeoutError(f"脚本执行超时 ({self.timeout}s): {script_name}")

        stdout = result.stdout[:self.max_output_chars]
        stderr = result.stderr[:self.max_output_chars]

        return {
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": str(result.returncode),
        }

    def list_scripts(self) -> list:
        """列出所有可用的诊断脚本"""
        scripts = sorted(self.approved_dir.glob("*.sh"))
        return [s.name for s in scripts]
