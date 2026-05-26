"""MySQL data source implementation."""
from typing import Any, Dict, List

from loguru import logger
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

from ops_agent.models.tools.base_datasource import BaseDataSource


class MySQLDataSource(BaseDataSource):
    dialect_name = "mysql"

    def __init__(self, config: dict):
        super().__init__(config)
        url = URL.create(
            "mysql+pymysql",
            username=config["user"],
            password=config.get("password", ""),
            host=config["host"],
            port=config.get("port", 3306),
            database=config["database"],
            query={"charset": config.get("charset", "utf8mb4")},
        )
        self.engine = create_engine(
            url,
            pool_pre_ping=True,
            connect_args={
                "connect_timeout": 10,
                "read_timeout": 10,
                "write_timeout": 10,
            },
        )
        logger.info("MySQL datasource configured: {}:{}/{}", config["host"], config.get("port", 3306), config["database"])

    def execute_query(self, sql: str) -> List[Dict[str, Any]]:
        with self.engine.connect() as conn:
            result = conn.execute(text(sql))
            rows = [dict(row._mapping) for row in result]
        return rows

    def health_check(self) -> bool:
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    def get_tables(self) -> List[str]:
        with self.engine.connect() as conn:
            result = conn.execute(
                text("SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA = :db"),
                {"db": self.config["database"]},
            )
            return [row[0] for row in result]

    def get_columns(self, table_name: str) -> List[Dict[str, Any]]:
        with self.engine.connect() as conn:
            result = conn.execute(
                text(
                    "SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT, COLUMN_COMMENT "
                    "FROM information_schema.COLUMNS "
                    "WHERE TABLE_SCHEMA = :db AND TABLE_NAME = :tbl "
                    "ORDER BY ORDINAL_POSITION"
                ),
                {"db": self.config["database"], "tbl": table_name},
            )
            return [
                {
                    "name": row[0],
                    "type": row[1],
                    "nullable": row[2] == "YES",
                    "default": row[3],
                    "comment": row[4] or "",
                }
                for row in result
            ]

    def get_sample_rows(self, table_name: str, limit: int = 3) -> List[Dict[str, Any]]:
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(f"SELECT * FROM `{table_name}` LIMIT {limit}"))
                return [dict(row._mapping) for row in result]
        except Exception:
            return []
