"""Persistent memory for resolved troubleshooting cases."""
import json
import re
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from ops_agent.models.category_registry import CategoryRegistry


class IncidentCaseMemory:
    """Stores compact incident cases and retrieves similar resolved cases."""

    def __init__(self, db_path: str | Path | None = None):
        self.db_path = Path(db_path or self._default_db_path())
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.category_registry = CategoryRegistry(self.db_path.parent / "case_categories.json")
        self._ensure_schema()

    def save_case(
        self,
        query: str,
        answer: str,
        symptoms: list[str],
        root_cause: str = "",
        solution: str = "",
        evidence: list[str] | None = None,
        status: str = "pending",
        category: str = "",
    ) -> dict[str, Any]:
        case_id = f"case_{uuid.uuid4().hex}"
        now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        tokens = sorted(self._tokens(" ".join([query, *symptoms, root_cause, solution])))
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO incident_cases
                    (case_id, query, answer, symptoms, root_cause, solution, evidence, status, category, tokens, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    case_id,
                    query,
                    answer,
                    json.dumps(symptoms, ensure_ascii=False),
                    root_cause,
                    solution,
                    json.dumps(evidence or [], ensure_ascii=False),
                    status,
                    category,
                    json.dumps(tokens, ensure_ascii=False),
                    now,
                    now,
                ),
            )
        return {"case_id": case_id, "status": status}

    def find_similar(
        self,
        query: str,
        symptoms: list[str] | None = None,
        min_score: float = 0.88,
    ) -> dict[str, Any] | None:
        query_tokens = self._tokens(" ".join([query, *(symptoms or [])]))
        symptom_tokens = self._tokens(" ".join(symptoms or []))
        best: dict[str, Any] | None = None

        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM incident_cases
                WHERE status IN ('resolved', 'auto_saved')
                ORDER BY updated_at DESC
                LIMIT 200
                """
            ).fetchall()

        for row in rows:
            case_tokens = set(json.loads(row["tokens"] or "[]"))
            score = self._score(query_tokens, case_tokens)
            if symptom_tokens:
                symptom_overlap = len(symptom_tokens & case_tokens) / len(symptom_tokens)
                score = max(score, round(symptom_overlap, 4))
            if score < min_score:
                continue
            item = dict(row)
            item["symptoms"] = json.loads(item["symptoms"] or "[]")
            item["evidence"] = json.loads(item["evidence"] or "[]")
            item["score"] = score
            if best is None or item["score"] > best["score"]:
                best = item

        return best

    def list_cases(
        self,
        status: str | None = None,
        limit: int = 200,
        query: str = "",
        category: str = "",
        symptom: str = "",
    ) -> list[dict[str, Any]]:
        sql = "SELECT * FROM incident_cases"
        params: list[Any] = []
        if status:
            sql += " WHERE status = ?"
            params.append(status)
        sql += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        items = [self._row_to_dict(row) for row in rows]
        return self._filter_cases(items, query=query, category=category, symptom=symptom)

    def get_case(self, case_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM incident_cases WHERE case_id = ?", (case_id,)).fetchone()
        return self._row_to_dict(row) if row else None

    def update_status(self, case_id: str, status: str) -> bool:
        now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        with self._connect() as conn:
            result = conn.execute(
                "UPDATE incident_cases SET status = ?, updated_at = ? WHERE case_id = ?",
                (status, now, case_id),
            )
            return result.rowcount > 0

    def update_category(self, case_id: str, category: str) -> bool:
        now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        with self._connect() as conn:
            result = conn.execute(
                "UPDATE incident_cases SET category = ?, updated_at = ? WHERE case_id = ?",
                (category, now, case_id),
            )
            return result.rowcount > 0

    def category_summary(self) -> list[dict[str, Any]]:
        groups: dict[str, dict[str, Any]] = {}
        for item in self.list_cases(limit=1000):
            name = item.get("category") or "未分类"
            group = groups.setdefault(name, {"name": name, "count": 0})
            group["count"] += 1
        for item in self.category_registry.list_categories():
            group = groups.setdefault(item["name"], {"name": item["name"], "count": 0})
            group["pinned"] = item.get("pinned", False)
            group["user_defined"] = True
        for group in groups.values():
            group.setdefault("pinned", False)
            group.setdefault("user_defined", False)
        return sorted(groups.values(), key=lambda item: (not item.get("pinned", False), -item["count"], item["name"]))

    def create_category(self, name: str) -> dict[str, Any]:
        return self.category_registry.create(name)

    def rename_category(self, old_name: str, new_name: str) -> dict[str, Any]:
        item = self.category_registry.rename(old_name, new_name)
        now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        with self._connect() as conn:
            conn.execute(
                "UPDATE incident_cases SET category = ?, updated_at = ? WHERE category = ?",
                (item["name"], now, old_name),
            )
        return item

    def set_category_pinned(self, name: str, pinned: bool) -> dict[str, Any]:
        return self.category_registry.set_pinned(name, pinned)

    def delete_category(self, name: str) -> bool:
        deleted = self.category_registry.delete(name)
        now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        with self._connect() as conn:
            conn.execute(
                "UPDATE incident_cases SET category = '', updated_at = ? WHERE category = ?",
                (now, name),
            )
        return deleted

    def delete_case(self, case_id: str) -> bool:
        with self._connect() as conn:
            result = conn.execute("DELETE FROM incident_cases WHERE case_id = ?", (case_id,))
            return result.rowcount > 0

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS incident_cases (
                    case_id TEXT PRIMARY KEY,
                    query TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    symptoms TEXT NOT NULL,
                    root_cause TEXT NOT NULL DEFAULT '',
                    solution TEXT NOT NULL DEFAULT '',
                    evidence TEXT NOT NULL DEFAULT '[]',
                    status TEXT NOT NULL DEFAULT 'pending',
                    category TEXT NOT NULL DEFAULT '',
                    tokens TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            columns = [row[1] for row in conn.execute("PRAGMA table_info(incident_cases)").fetchall()]
            if "category" not in columns:
                conn.execute("ALTER TABLE incident_cases ADD COLUMN category TEXT NOT NULL DEFAULT ''")

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
        item = dict(row)
        item["symptoms"] = json.loads(item["symptoms"] or "[]")
        item["evidence"] = json.loads(item["evidence"] or "[]")
        item["tokens"] = json.loads(item["tokens"] or "[]")
        return item

    @staticmethod
    def _filter_cases(
        items: list[dict[str, Any]],
        query: str = "",
        category: str = "",
        symptom: str = "",
    ) -> list[dict[str, Any]]:
        query_lower = query.strip().lower()
        symptom_lower = symptom.strip().lower()
        filtered = []
        for item in items:
            if category and item.get("category") != category:
                continue
            if query_lower:
                haystack = " ".join([
                    item.get("query", ""),
                    item.get("answer", ""),
                    item.get("root_cause", ""),
                    item.get("solution", ""),
                    " ".join(item.get("symptoms", [])),
                ]).lower()
                if query_lower not in haystack:
                    continue
            if symptom_lower and not any(symptom_lower in value.lower() for value in item.get("symptoms", [])):
                continue
            filtered.append(item)
        return filtered

    @staticmethod
    def _tokens(text: str) -> set[str]:
        raw = re.findall(r"[A-Za-z0-9_.:-]+|[\u4e00-\u9fff]{2,}", text.lower())
        normalized = set(raw)
        phrase_map = {
            "connection refused": ["connection", "refused"],
            "out of memory": ["out", "memory"],
            "permission denied": ["permission", "denied"],
        }
        lower = text.lower()
        for phrase, parts in phrase_map.items():
            if phrase in lower:
                normalized.add(phrase)
                normalized.update(parts)
        return {token for token in normalized if len(token) >= 2}

    @staticmethod
    def _score(query_tokens: set[str], case_tokens: set[str]) -> float:
        if not query_tokens or not case_tokens:
            return 0.0
        overlap = len(query_tokens & case_tokens)
        coverage = overlap / len(query_tokens)
        containment = overlap / min(len(query_tokens), len(case_tokens))
        return round((coverage * 0.65) + (containment * 0.35), 4)

    @staticmethod
    def _default_db_path() -> Path:
        from config.settings import settings

        return Path(settings.incident_cases_db_path)
