"""MySQL 数据库连接器"""
from typing import List, Dict, Any
from contextlib import contextmanager
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from loguru import logger

from config.settings import settings
from ops_agent.utils.exceptions import DatabaseConnectionError, SQLError


class DatabaseConnector:
    """MySQL 数据库连接器"""

    def __init__(self):
        self.url = settings.mysql_url
        self.engine = create_engine(
            self.url,
            pool_size=5,
            max_overflow=10,
            pool_recycle=3600,
            pool_pre_ping=True,
            echo=settings.debug,
        )
        logger.info("数据库连接器初始化: {}:{}", settings.mysql_host, settings.mysql_port)

    def health_check(self) -> bool:
        """检查数据库连接"""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error("数据库连接失败: {}", e)
            return False

    def execute_query(self, sql: str, params: dict | None = None) -> List[Dict[str, Any]]:
        """执行 SELECT 查询，返回字典列表"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(sql), params or {})
                rows = result.fetchall()
                if rows:
                    columns = list(result.keys())
                    return [dict(zip(columns, row)) for row in rows]
                return []
        except SQLAlchemyError as e:
            raise SQLError(f"SQL 执行失败: {e}") from e

    def execute_write(self, sql: str, params: dict | None = None) -> int:
        """执行 INSERT/UPDATE/DELETE，返回影响行数"""
        try:
            with self.engine.connect() as conn:
                with conn.begin():
                    result = conn.execute(text(sql), params or {})
                    return result.rowcount
        except SQLAlchemyError as e:
            raise SQLError(f"SQL 写入失败: {e}") from e

    def get_table_names(self) -> List[str]:
        """获取所有表名"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text("SELECT TABLE_NAME FROM information_schema.TABLES "
                         "WHERE TABLE_SCHEMA = :db AND TABLE_TYPE = 'BASE TABLE'"),
                    {"db": settings.mysql_database}
                )
                return [row[0] for row in result.fetchall()]
        except SQLAlchemyError as e:
            raise DatabaseConnectionError(f"获取表列表失败: {e}") from e

    def get_table_schema(self, table_name: str) -> List[Dict[str, Any]]:
        """获取表结构信息"""
        sql = """
        SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT, COLUMN_COMMENT
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = :db AND TABLE_NAME = :table
        ORDER BY ORDINAL_POSITION
        """
        return self.execute_query(sql, {"db": settings.mysql_database, "table": table_name})

    def get_sample_rows(self, table_name: str, limit: int = 3) -> List[Dict[str, Any]]:
        """获取表示例数据"""
        return self.execute_query(f"SELECT * FROM `{table_name}` LIMIT {limit}")


# 全局单例
_db_connector: DatabaseConnector | None = None


def get_db_connector() -> DatabaseConnector:
    global _db_connector
    if _db_connector is None:
        _db_connector = DatabaseConnector()
    return _db_connector
