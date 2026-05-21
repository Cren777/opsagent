"""Text2SQL 生成器：自然语言 → SQL"""
import re
from loguru import logger

from ops_agent.models.llm.client import get_llm_client, LLMError
from ops_agent.models.text2sql.schema_manager import SchemaManager
from ops_agent.models.text2sql.sql_validator import SQLValidator
from ops_agent.utils.exceptions import SQLError


_TEXT2SQL_PROMPT = """你是一个MySQL专家。根据以下数据库Schema，将用户的自然语言问题转换为MySQL SELECT语句。

{db_schema}
{join_hints}

## 规则
1. 只生成 SELECT 语句，不要生成其他内容
2. 适当的 JOIN 和 GROUP BY
3. 必须添加 LIMIT 100
4. 使用中文友好的列别名（如果合适）
5. 如果问题中涉及日期，使用 CURRENT_TIMESTAMP 或 DATE_SUB/NOW() 函数
6. 只输出SQL，不要解释

## 示例
问：最近一周的critical级别告警有哪些？
SQL：SELECT title, message, created_at FROM alerts WHERE severity = 'critical' AND created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY) ORDER BY created_at DESC LIMIT 100;

问：每个服务器的服务数量
SQL：SELECT s.hostname, COUNT(sv.service_id) AS 服务数量 FROM servers s LEFT JOIN services sv ON s.server_id = sv.server_id GROUP BY s.server_id, s.hostname ORDER BY 服务数量 DESC LIMIT 100;

## 用户问题
{question}

SQL："""


class Text2SQLGenerator:
    """Text2SQL 生成器"""

    def __init__(self):
        self.schema_manager = SchemaManager()
        self.validator = SQLValidator()

    async def generate(self, question: str) -> str:
        """根据自然语言问题生成 SQL

        Args:
            question: 用户自然语言问题

        Returns:
            生成的 SQL 语句
        """
        schema_prompt = self.schema_manager.get_schema_prompt()
        join_hints = self.schema_manager.get_join_hints()

        prompt = _TEXT2SQL_PROMPT.format(
            db_schema=schema_prompt,
            join_hints=join_hints,
            question=question,
        )

        messages = [{"role": "user", "content": prompt}]
        client = get_llm_client()

        try:
            response = await client.chat(
                messages,
                temperature=0.0,
                max_tokens=1024,
            )
        except LLMError as e:
            raise SQLError(f"Text2SQL 生成失败: {e}") from e

        sql = self._extract_sql(response)
        logger.info("Text2SQL: '{}' → {}", question[:50], sql[:100])

        self.validator.validate(sql)
        return sql

    def _extract_sql(self, response: str) -> str:
        """从 LLM 响应中提取 SQL 语句"""
        response = response.strip()

        # 去掉可能的 markdown sql 标记
        response = re.sub(r"^```(?:sql)?\s*", "", response)
        response = re.sub(r"\s*```$", "", response)

        # 确保SQL以分号结束（但不要重复分号）
        response = response.rstrip(";")
        return response
