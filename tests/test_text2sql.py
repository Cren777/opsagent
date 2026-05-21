"""Text2SQL 安全校验器测试"""
import pytest
from ops_agent.models.text2sql.sql_validator import SQLValidator, DangerousSQLError


class TestSQLValidator:
    def setup_method(self):
        self.validator = SQLValidator()

    def test_valid_select(self):
        """合法的SELECT应通过"""
        self.validator.validate(
            "SELECT hostname, ip FROM servers WHERE status = 'online' LIMIT 100"
        )

    def test_forbidden_drop(self):
        """DROP语句应被拒绝"""
        with pytest.raises(DangerousSQLError):
            self.validator.validate("DROP TABLE servers")

    def test_forbidden_delete(self):
        """DELETE语句应被拒绝"""
        with pytest.raises(DangerousSQLError):
            self.validator.validate("DELETE FROM alerts WHERE alert_id = 1")

    def test_forbidden_insert(self):
        """INSERT语句应被拒绝"""
        with pytest.raises(DangerousSQLError):
            self.validator.validate("INSERT INTO servers VALUES (1, 'test')")

    def test_forbidden_update(self):
        """UPDATE语句应被拒绝"""
        with pytest.raises(DangerousSQLError):
            self.validator.validate("UPDATE servers SET status = 'offline'")

    def test_requires_limit(self):
        """SELECT必须含LIMIT"""
        with pytest.raises(DangerousSQLError):
            self.validator.validate("SELECT * FROM servers")

    def test_limit_too_large(self):
        """LIMIT值过大"""
        with pytest.raises(DangerousSQLError):
            self.validator.validate("SELECT * FROM servers LIMIT 500")

    def test_sql_injection_blocked(self):
        """SQL注入应被检测"""
        with pytest.raises(DangerousSQLError):
            self.validator.validate(
                "SELECT * FROM users WHERE username = 'admin' OR '1'='1' LIMIT 10"
            )

    def test_all_forbidden_keywords(self):
        """所有危险关键词都被拦截"""
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
