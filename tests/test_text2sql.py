"""Tests for Text2SQL safety and SQL normalization."""
import sys
import types

import pytest

sys.modules.setdefault(
    "loguru",
    types.SimpleNamespace(logger=types.SimpleNamespace(info=lambda *a, **k: None, warning=lambda *a, **k: None)),
)
sys.modules.setdefault(
    "ops_agent.models.llm.client",
    types.SimpleNamespace(LLMError=Exception, get_llm_client=lambda: None),
)

from ops_agent.models.text2sql.generator import Text2SQLGenerator
from ops_agent.models.text2sql.sql_validator import DangerousSQLError, SQLValidator
from ops_agent.models.tools.clickhouse_source import ClickHouseDataSource


class FakeClickHouseSource:
    dialect_name = "clickhouse"


class TestSQLValidator:
    def setup_method(self):
        self.validator = SQLValidator()

    def test_valid_select(self):
        self.validator.validate("SELECT hostname, ip FROM servers WHERE status = 'online' LIMIT 100")

    def test_forbidden_drop(self):
        with pytest.raises(DangerousSQLError):
            self.validator.validate("DROP TABLE servers")

    def test_forbidden_delete(self):
        with pytest.raises(DangerousSQLError):
            self.validator.validate("DELETE FROM alerts WHERE alert_id = 1")

    def test_forbidden_insert(self):
        with pytest.raises(DangerousSQLError):
            self.validator.validate("INSERT INTO servers VALUES (1, 'test')")

    def test_forbidden_update(self):
        with pytest.raises(DangerousSQLError):
            self.validator.validate("UPDATE servers SET status = 'offline'")

    def test_requires_limit(self):
        with pytest.raises(DangerousSQLError):
            self.validator.validate("SELECT * FROM servers")

    def test_limit_too_large(self):
        with pytest.raises(DangerousSQLError):
            self.validator.validate("SELECT * FROM servers LIMIT 500")

    def test_sql_injection_blocked(self):
        with pytest.raises(DangerousSQLError):
            self.validator.validate("SELECT * FROM users WHERE username = 'admin' OR '1'='1' LIMIT 10")

    def test_all_forbidden_keywords(self):
        dangerous = [
            "DROP TABLE servers",
            "DELETE FROM alerts WHERE 1=1",
            "INSERT INTO servers VALUES(1)",
            "UPDATE servers SET status='x' LIMIT 1",
            "ALTER TABLE servers ADD COLUMN x INT",
            "TRUNCATE TABLE alerts",
            "CREATE TABLE test (id INT)",
            "GRANT ALL ON *.* TO user",
        ]
        for sql in dangerous:
            with pytest.raises(DangerousSQLError):
                self.validator.validate(sql)


class TestText2SQLGenerator:
    def setup_method(self):
        self.generator = Text2SQLGenerator()
        self.generator.schema_manager._datasource = FakeClickHouseSource()
        self.generator.schema_manager._cache = [
            {
                "table": "hawkeye_dwd_intel_content",
                "columns": [],
                "sample_rows": [],
            }
        ]

    def test_extract_sql_from_markdown_and_explanation(self):
        sql = self.generator._extract_sql(
            "```sql\nSELECT COUNT(*) AS total_count FROM hawkeye_dwd_intel_content LIMIT 100;\n```\n"
            "\u8bf4\u660e\uff1a\u7edf\u8ba1\u603b\u6570"
        )

        assert sql == "SELECT COUNT(*) AS total_count FROM hawkeye_dwd_intel_content LIMIT 100"

    def test_normalize_known_chinese_alias(self):
        sql = self.generator._extract_sql(
            "SELECT COUNT(*) AS \u6570\u636e\u6761\u6570 FROM hawkeye_dwd_intel_content LIMIT 100"
        )

        assert "\u6570\u636e\u6761\u6570" not in sql
        assert "AS total_count" in sql

    def test_normalize_unknown_non_ascii_alias(self):
        sql = self.generator._extract_sql(
            "SELECT COUNT(*) AS \u4e2d\u6587\u522b\u540d FROM hawkeye_dwd_intel_content LIMIT 100"
        )

        assert "\u4e2d\u6587\u522b\u540d" not in sql
        assert "AS value" in sql

    def test_rule_based_count_uses_selected_table_and_ascii_alias(self):
        sql = self.generator._try_generate_rule_based_sql(
            "\u5e2e\u6211\u67e5\u8be2hawkeye_dwd_intel_content\u8868\u4e2d\u6709\u591a\u5c11\u6761\u6570\u636e"
        )

        assert sql == "SELECT COUNT(*) AS total_count FROM `hawkeye_dwd_intel_content` LIMIT 100"

    def test_rule_based_sample_row_uses_random_order(self):
        sql = self.generator._try_generate_rule_based_sql(
            "\u4ece\u8868\u4e2d\u968f\u4fbf\u7b5b\u9009\u51fa\u4e00\u6761\u6570\u636e\u8fdb\u884c\u5c55\u793a "
            "Target table: hawkeye_dwd_intel_content"
        )

        assert sql == "SELECT * FROM `hawkeye_dwd_intel_content` ORDER BY rand() LIMIT 1"

    def test_rule_based_detail_query_filters_by_mentioned_sample_value(self):
        self.generator.schema_manager._datasource.dialect_name = "sqlite"
        self.generator.schema_manager._cache = [
            {
                "table": "ops_metrics",
                "columns": [
                    {"name": "采集时间", "type": "TEXT"},
                    {"name": "服务器", "type": "TEXT"},
                    {"name": "CPU使用率", "type": "REAL"},
                ],
                "sample_rows": [
                    {"采集时间": "2026-05-26 09:00:00", "服务器": "web-01", "CPU使用率": 72.5},
                    {"采集时间": "2026-05-26 09:00:00", "服务器": "web-02", "CPU使用率": 48.3},
                    {"采集时间": "2026-05-26 09:05:00", "服务器": "web-01", "CPU使用率": 75.2},
                ],
            }
        ]

        sql = self.generator._try_generate_rule_based_sql("展示ops_metrics表格中web-01服务器的详细数据")

        assert sql == 'SELECT * FROM "ops_metrics" WHERE "服务器" = \'web-01\' LIMIT 100'


class TestClickHouseSource:
    def test_prepare_sql_normalizes_alias_and_qualifies_current_database(self):
        source = ClickHouseDataSource.__new__(ClickHouseDataSource)
        source.config = {
            "database": "hawkeye_test",
            "selected_tables": ["hawkeye_dwd_intel_content"],
        }

        sql = source._prepare_sql(
            "SELECT COUNT(*) AS \u6570\u636e\u6761\u6570 FROM hawkeye_dwd_intel_content LIMIT 100"
        )

        assert sql == "SELECT COUNT(*) AS value FROM `hawkeye_test`.`hawkeye_dwd_intel_content` LIMIT 100"
