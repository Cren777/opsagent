"""SQL 安全校验器"""
import re
from ops_agent.utils.exceptions import DangerousSQLError, SQLError


# 禁止的 SQL 关键词（不区分大小写）
_FORBIDDEN_KEYWORDS = [
    r"\bDROP\b",
    r"\bDELETE\b",
    r"\bINSERT\b",
    r"\bUPDATE\b",
    r"\bALTER\b",
    r"\bTRUNCATE\b",
    r"\bCREATE\b",
    r"\bEXEC\b",
    r"\bEXECUTE\b",
    r"\bGRANT\b",
    r"\bREVOKE\b",
    r"\bRENAME\b",
    r"\bREPLACE\b",
    r"\bMERGE\b",
    r"\bUNION\b",  # UNION 可能用于注入
]


class SQLValidator:
    """SQL 安全校验"""

    @staticmethod
    def validate(sql: str) -> None:
        """校验 SQL 语句的安全性

        Args:
            sql: SQL 语句

        Raises:
            DangerousSQLError: 发现危险操作
            SQLError: SQL 语法错误
        """
        sql_upper = sql.upper()

        # 1. 检查危险关键词
        for pattern in _FORBIDDEN_KEYWORDS:
            if re.search(pattern, sql_upper):
                keyword = pattern.replace(r"\b", "")
                raise DangerousSQLError(f"禁止的SQL操作: {keyword}")

        # 2. 必须以 SELECT 开头
        if not sql_upper.strip().startswith("SELECT"):
            raise DangerousSQLError("只允许 SELECT 查询")

        # 3. 必须有 LIMIT
        if "LIMIT" not in sql_upper:
            raise DangerousSQLError("SELECT 语句必须包含 LIMIT")

        # 4. 检查 LIMIT 值
        limit_match = re.search(r"LIMIT\s+(\d+)", sql_upper)
        if limit_match:
            limit_val = int(limit_match.group(1))
            if limit_val > 200:
                raise DangerousSQLError(f"LIMIT 值过大 ({limit_val})，最大允许 200")

        # 5. 基础 SQL 注入检测
        dangerous_patterns = [
            r"'.*OR\s+'1'='1",
            r"'.*OR\s+1=1",
            r"'.*--",
            r"'\s*;\s*SELECT",
        ]
        for pattern in dangerous_patterns:
            if re.search(pattern, sql_upper):
                raise DangerousSQLError("检测到可能的SQL注入")
