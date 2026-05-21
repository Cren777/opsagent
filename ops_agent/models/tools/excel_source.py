"""Excel/CSV data source — loads file into in-memory SQLite for querying."""
import os
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
        self._load_file(config['file_path'], config.get('sheet_name', ''))

    def _load_file(self, file_path: str, sheet_name: str):
        if not os.path.exists(file_path):
            logger.warning("文件不存在: {}", file_path)
            return

        import pandas as pd

        ext = os.path.splitext(file_path)[1].lower()
        if ext == '.csv':
            df = pd.read_csv(file_path)
        elif ext in ('.xlsx', '.xls'):
            df = pd.read_excel(file_path, sheet_name=sheet_name or 0)
        else:
            raise ValueError(f"不支持的文件格式: {ext}")

        # Use filename without extension as table name
        table_name = os.path.splitext(os.path.basename(file_path))[0]
        table_name = table_name.replace('-', '_').replace(' ', '_')
        df.to_sql(table_name, self.conn, index=False)
        self._tables.append(table_name)

        logger.info("Excel/CSV 文件已加载: {} → 表 '{}' ({} 行, {} 列)",
                     file_path, table_name, len(df), len(df.columns))

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
