"""Persistent user-managed category registry."""
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


class CategoryRegistry:
    """Stores user-created category metadata such as pinned order."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def list_categories(self) -> list[dict[str, Any]]:
        categories = list(self._read().values())
        return sorted(
            categories,
            key=lambda item: (
                not item.get("pinned", False),
                item.get("sort_order", 0),
                item.get("name", ""),
            ),
        )

    def create(self, name: str) -> dict[str, Any]:
        safe_name = self._safe_name(name)
        data = self._read()
        now = self._now()
        item = data.get(safe_name) or {
            "name": safe_name,
            "pinned": False,
            "sort_order": 0,
            "created_at": now,
        }
        item["updated_at"] = now
        data[safe_name] = item
        self._write(data)
        return item

    def rename(self, old_name: str, new_name: str) -> dict[str, Any]:
        old_safe = self._safe_name(old_name)
        new_safe = self._safe_name(new_name)
        data = self._read()
        now = self._now()
        item = data.pop(old_safe, {
            "created_at": now,
            "pinned": False,
            "sort_order": 0,
        })
        item["name"] = new_safe
        item["updated_at"] = now
        data[new_safe] = item
        self._write(data)
        return item

    def set_pinned(self, name: str, pinned: bool) -> dict[str, Any]:
        safe_name = self._safe_name(name)
        data = self._read()
        item = data.get(safe_name) or self.create(safe_name)
        data = self._read()
        item = data[safe_name]
        item["pinned"] = bool(pinned)
        item["updated_at"] = self._now()
        data[safe_name] = item
        self._write(data)
        return item

    def delete(self, name: str) -> bool:
        safe_name = self._safe_name(name)
        data = self._read()
        existed = safe_name in data
        data.pop(safe_name, None)
        self._write(data)
        return existed

    def _read(self) -> dict[str, dict[str, Any]]:
        if not self.path.exists():
            return {}
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
        return {item["name"]: item for item in raw.get("categories", []) if item.get("name")}

    def _write(self, data: dict[str, dict[str, Any]]) -> None:
        payload = {"categories": list(data.values())}
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _safe_name(name: str) -> str:
        normalized = str(name or "").replace("\\", "/").strip("/")
        if not normalized:
            raise ValueError("分类名称不能为空")
        if ".." in Path(normalized).parts:
            raise ValueError("非法的分类路径")
        parts = [re.sub(r"[^A-Za-z0-9._\-\u4e00-\u9fff]+", "_", part) for part in normalized.split("/") if part]
        return "/".join(parts)

    @staticmethod
    def _now() -> str:
        return datetime.utcnow().isoformat(timespec="seconds") + "Z"
