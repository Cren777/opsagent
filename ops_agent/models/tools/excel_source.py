"""Excel/CSV data source — loads file into in-memory SQLite for querying."""
import os
import re
import sqlite3
from typing import List, Dict, Any
from loguru import logger

from ops_agent.models.tools.base_datasource import BaseDataSource


class ExcelCSVDataSource(BaseDataSource):
    dialect_name = "sqlite"

    def __init__(self, config: dict):
        super().__init__(config)
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self._tables: List[str] = []
        files = config.get("files") or []
        if files:
            for file_config in files:
                self._load_file(
                    file_config["file_path"],
                    file_config.get("sheet_name", ""),
                    file_config.get("original_filename", ""),
                )
        elif config.get("file_path"):
            self._load_file(config["file_path"], config.get("sheet_name", ""), config.get("original_filename", ""))

    def _load_file(self, file_path: str, sheet_name: str, original_filename: str = ""):
        if not os.path.exists(file_path):
            logger.warning("文件不存在: {}", file_path)
            return

        import pandas as pd

        ext = os.path.splitext(file_path)[1].lower()
        if ext == '.csv':
            df = self._read_csv(file_path)
        elif ext in ('.xlsx', '.xls'):
            df = pd.read_excel(file_path, sheet_name=sheet_name or 0)
        else:
            raise ValueError(f"不支持的文件格式: {ext}")

        table_name = self._unique_table_name(original_filename or os.path.basename(file_path))
        df.to_sql(table_name, self.conn, index=False)
        self._tables.append(table_name)

        logger.info("Excel/CSV 文件已加载: {} → 表 '{}' ({} 行, {} 列)",
                     file_path, table_name, len(df), len(df.columns))

    def _read_csv(self, file_path: str):
        import pandas as pd

        last_error = None
        for encoding in ("utf-8-sig", "utf-8", "gbk"):
            try:
                return pd.read_csv(file_path, encoding=encoding)
            except UnicodeDecodeError as e:
                last_error = e
        if last_error:
            raise last_error
        return pd.read_csv(file_path)

    def _unique_table_name(self, filename: str) -> str:
        stem = os.path.splitext(os.path.basename(filename))[0]
        table_name = re.sub(r"\W+", "_", stem, flags=re.UNICODE).strip("_")
        if not table_name:
            table_name = "uploaded_table"
        candidate = table_name
        index = 2
        while candidate in self._tables:
            candidate = f"{table_name}_{index}"
            index += 1
        return candidate

    def execute_query(self, sql: str) -> List[Dict[str, Any]]:
        cursor = self.conn.execute(sql)
        return [dict(row) for row in cursor.fetchall()]

    def health_check(self) -> bool:
        try:
            self.conn.execute("SELECT 1")
            return True
        except Exception:
            return False

    def get_tables(self) -> List[str]:
        return self._tables

    def get_columns(self, table_name: str) -> List[Dict[str, Any]]:
        cursor = self.conn.execute(f"PRAGMA table_info('{table_name}')")
        return [
            {
                "name": row[1],
                "type": row[2],
                "nullable": not row[3],
                "default": row[4] if row[4] is not None else "",
                "comment": "",
            }
            for row in cursor.fetchall()
        ]

    def get_sample_rows(self, table_name: str, limit: int = 3) -> List[Dict[str, Any]]:
        try:
            cursor = self.conn.execute(f"SELECT * FROM '{table_name}' LIMIT {limit}")
            return [dict(row) for row in cursor.fetchall()]
        except Exception:
            return []
