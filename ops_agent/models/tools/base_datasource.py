"""Abstract base class for data source connectors."""
from abc import ABC, abstractmethod
from typing import List, Dict, Any


class BaseDataSource(ABC):
    """Abstract data source for Text2SQL queries."""

    def __init__(self, config: dict):
        self.config = config

    @abstractmethod
    def execute_query(self, sql: str) -> List[Dict[str, Any]]:
        """Execute a SELECT query and return rows as dicts."""

    @abstractmethod
    def health_check(self) -> bool:
        """Check if the data source is reachable."""

    @abstractmethod
    def get_tables(self) -> List[str]:
        """Return list of table names."""

    @abstractmethod
    def get_columns(self, table_name: str) -> List[Dict[str, Any]]:
        """Return columns for a table: [{name, type, nullable, default, comment}]."""

    @abstractmethod
    def get_sample_rows(self, table_name: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Return sample rows from a table."""

    @property
    @abstractmethod
    def dialect_name(self) -> str:
        """SQL dialect name: 'mysql', 'clickhouse', 'sqlite'."""
