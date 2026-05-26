"""ClickHouse data source implementation."""
import re
from typing import List, Dict, Any
from loguru import logger

from ops_agent.models.tools.base_datasource import BaseDataSource


class ClickHouseDataSource(BaseDataSource):
    dialect_name = "clickhouse"

    def __init__(self, config: dict):
        super().__init__(config)
        try:
            from clickhouse_connect import get_client
            self.client = get_client(
                host=config['host'],
                port=config.get('port', 8123),
                username=config.get('user', 'default'),
                password=config.get('password', ''),
                database=config.get('database', 'default'),
                connect_timeout=10,
            )
            logger.info("ClickHouse 数据源已连接: {}:{}", config['host'], config.get('port', 8123))
        except ImportError:
            raise ImportError("请安装 clickhouse-connect: pip install clickhouse-connect")

    def execute_query(self, sql: str) -> List[Dict[str, Any]]:
        sql = self._prepare_sql(sql)
        result = self.client.query(sql)
        columns = result.column_names
        rows = []
        for row in result.result_rows:
            rows.append(dict(zip(columns, row)))
        return rows

    def _prepare_sql(self, sql: str) -> str:
        """Normalize generated SQL for the configured ClickHouse database."""
        sql = re.sub(
            r"\bAS\s+(`[^`\x00-\x7f]+`|\"[^\"\x00-\x7f]+\"|[^\s,)\x00-\x7f]+)",
            "AS value",
            sql,
            flags=re.IGNORECASE,
        )

        db = self.config.get('database', 'default')
        if not db:
            return sql

        table_names = set(self.config.get("selected_tables") or [])
        if not table_names:
            try:
                table_names = set(self.get_tables())
            except Exception:
                table_names = set()

        for table in sorted(table_names, key=len, reverse=True):
            quoted_table = re.escape(table)
            qualified = f"`{db}`.`{table}`"
            sql = re.sub(
                rf"(\bFROM\s+)(`?){quoted_table}\2(?!\s*\.)",
                rf"\1{qualified}",
                sql,
                flags=re.IGNORECASE,
            )
            sql = re.sub(
                rf"(\bJOIN\s+)(`?){quoted_table}\2(?!\s*\.)",
                rf"\1{qualified}",
                sql,
                flags=re.IGNORECASE,
            )

        return sql

    def health_check(self) -> bool:
        try:
            self.client.command("SELECT 1")
            return True
        except Exception:
            return False

    def get_tables(self) -> List[str]:
        db = self.config.get('database', 'default')
        result = self.client.query(f"SHOW TABLES FROM {db}")
        return [row[0] for row in result.result_rows]

    def get_columns(self, table_name: str) -> List[Dict[str, Any]]:
        db = self.config.get('database', 'default')
        result = self.client.query(f"DESCRIBE TABLE {db}.{table_name}")
        return [
            {
                "name": row[0],
                "type": row[1],
                "nullable": "Nullable" in str(row[1]),
                "default": row[2] if len(row) > 2 else "",
                "comment": row[3] if len(row) > 3 else "",
            }
            for row in result.result_rows
        ]

    def get_sample_rows(self, table_name: str, limit: int = 3) -> List[Dict[str, Any]]:
        try:
            db = self.config.get('database', 'default')
            result = self.client.query(f"SELECT * FROM {db}.{table_name} LIMIT {limit}")
            return [dict(zip(result.column_names, row)) for row in result.result_rows]
        except Exception:
            return []
