"""数据库 Schema 管理器：内省数据库结构，生成 Text2SQL 提示"""
from typing import List, Dict, Any, Optional
from loguru import logger

from ops_agent.models.tools.base_datasource import BaseDataSource
from ops_agent.utils.exceptions import DatabaseConnectionError


class SchemaManager:
    """数据库 Schema 管理，支持多种数据源"""

    def __init__(self, datasource: Optional[BaseDataSource] = None):
        self._datasource = datasource
        self._cache: List[Dict[str, Any]] | None = None

    def set_datasource(self, datasource: BaseDataSource):
        """设置/切换数据源，清除缓存"""
        self._datasource = datasource
        self._cache = None

    def _get_datasource(self) -> BaseDataSource:
        if self._datasource is None:
            from ops_agent.models.tools.datasource_factory import get_active_datasource
            ds = get_active_datasource()
            if ds is None:
                raise DatabaseConnectionError("无法获取数据源连接")
            self._datasource = ds
        return self._datasource

    def refresh(self):
        """刷新 Schema 缓存"""
        db = self._get_datasource()
        try:
            tables = db.get_tables()
            schema_info = []
            for table in tables:
                columns = db.get_columns(table)
                sample = db.get_sample_rows(table)
                schema_info.append({
                    "table": table,
                    "columns": columns,
                    "sample_rows": sample,
                })
            self._cache = schema_info
            logger.info("Schema 缓存已更新: {} 张表 (方言: {})", len(tables), db.dialect_name)
        except Exception as e:
            raise DatabaseConnectionError(f"Schema 内省失败: {e}") from e

    def get_schema_prompt(self) -> str:
        """生成 Text2SQL 用的 Schema 提示文本"""
        if self._cache is None:
            self.refresh()

        parts = ["## 数据库 Schema\n"]
        for table_info in self._cache:
            table = table_info["table"]
            parts.append(f"### 表: {table}")
            parts.append("| 列名 | 类型 | 可为空 | 默认值 | 说明 |")
            parts.append("|------|------|--------|--------|------|")
            for col in table_info["columns"]:
                parts.append(
                    f"| {col['name']} | {col['type']} | "
                    f"{'YES' if col['nullable'] else 'NO'} | {col['default'] or '-'} | "
                    f"{col['comment'] or '-'} |"
                )

            samples = table_info["sample_rows"]
            if samples:
                parts.append(f"\n示例数据（前3行）:")
                keys = list(samples[0].keys())
                parts.append("| " + " | ".join(keys) + " |")
                parts.append("|" + "|".join(["------"] * len(keys)) + "|")
                for row in samples:
                    parts.append("| " + " | ".join(str(row.get(k, "")) for k in keys) + " |")
            parts.append("")

        return "\n".join(parts)

    def get_table_list(self) -> List[str]:
        """获取所有表名列表"""
        if self._cache is None:
            self.refresh()
        return [t["table"] for t in self._cache]

    def get_join_hints(self) -> str:
        """生成表关联提示"""
        table_list = self.get_table_list()
        hints = {
            "servers": "servers.server_id 可关联 services, alerts, tickets, performance_metrics",
            "services": "services.server_id 关联 servers.server_id",
            "alerts": "alerts.server_id 关联 servers.server_id",
            "tickets": "tickets.server_id 关联 servers.server_id, tickets.user_id 关联 users.user_id",
            "performance_metrics": "performance_metrics.server_id 关联 servers.server_id",
            "users": "users.user_id 关联 tickets.user_id",
        }
        parts = ["\n## 表关联关系\n"]
        for table, hint in hints.items():
            if table in table_list:
                parts.append(f"- {hint}")
        return "\n".join(parts)
