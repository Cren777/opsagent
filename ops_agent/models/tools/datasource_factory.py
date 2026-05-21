"""Factory that reads active config from config DB and returns the right DataSource."""
from typing import Optional
from loguru import logger

from ops_agent.models.tools.base_datasource import BaseDataSource
from ops_agent.models.tools.mysql_source import MySQLDataSource
from ops_agent.models.tools.clickhouse_source import ClickHouseDataSource
from ops_agent.models.tools.excel_source import ExcelCSVDataSource


_data_source_cache: Optional[BaseDataSource] = None


def get_active_datasource() -> Optional[BaseDataSource]:
    """Get or create the active data source from config DB."""
    global _data_source_cache

    try:
        from ops_agent.api.services.config_service import list_datasources
        sources = list_datasources()
        active = next((s for s in sources if s.get("is_active")), None)

        if not active:
            # Fallback to settings-based MySQL
            from config.settings import settings
            from ops_agent.models.tools.mysql_source import MySQLDataSource
            logger.info("配置数据库中无活跃数据源，回退到 settings MySQL")
            return MySQLDataSource({
                "host": settings.mysql_host,
                "port": settings.mysql_port,
                "user": settings.mysql_user,
                "password": settings.mysql_password,
                "database": settings.mysql_database,
                "charset": settings.mysql_charset,
            })

        config = active["config"]
        ds_type = active["type"]

        if ds_type == "mysql":
            _data_source_cache = MySQLDataSource(config)
        elif ds_type == "clickhouse":
            _data_source_cache = ClickHouseDataSource(config)
        elif ds_type == "excel_csv":
            _data_source_cache = ExcelCSVDataSource(config)
        else:
            logger.warning("不支持的数据源类型: {}", ds_type)
            return None

        return _data_source_cache

    except Exception as e:
        logger.error("创建数据源失败: {}", e)
        return None


def invalidate_datasource_cache():
    """Invalidate cached data source so next call re-reads config."""
    global _data_source_cache
    _data_source_cache = None
