"""Text2SQL generator: natural language -> SELECT SQL."""
import re

from loguru import logger

from ops_agent.models.llm.client import LLMError, get_llm_client
from ops_agent.models.text2sql.schema_manager import SchemaManager
from ops_agent.models.text2sql.sql_validator import SQLValidator
from ops_agent.utils.exceptions import SQLError


_TEXT2SQL_PROMPT = """You are a database SQL expert. Convert the user's question into one executable SELECT statement for the current datasource dialect.

{db_schema}
{join_hints}
{dialect_guidance}

Rules:
1. Output exactly one SELECT statement. Do not output explanations or Markdown.
2. Use only tables and columns shown in the schema. Prefer the user's currently selected datasource tables.
3. Add LIMIT 100 unless the SQL syntax does not allow it.
4. Aliases must be ASCII snake_case, such as total_count or alert_count. Never use Chinese aliases.
5. Use date/time functions supported by the current SQL dialect.

Examples:
Q: How many rows are in the alerts table?
SQL: SELECT COUNT(*) AS total_count FROM alerts LIMIT 100;

Q: Count services by host.
SQL: SELECT s.hostname, COUNT(sv.service_id) AS service_count FROM servers s LEFT JOIN services sv ON s.server_id = sv.server_id GROUP BY s.server_id, s.hostname ORDER BY service_count DESC LIMIT 100;

User question:
{question}

SQL:"""


_COUNT_QUESTION_RE = re.compile(
    "|".join(
        [
            r"\u591a\u5c11\u6761",  #多少条
            r"\u51e0\u6761",  # 几条
            r"\u6761\u6570(?!\u636e)",  # row count, but not "one row of data"
            r"\u603b\u6570",  # 总数
            r"\u6570\u91cf",  # 数量
            r"count",
        ]
    ),
    flags=re.IGNORECASE,
)

_SAMPLE_ROW_QUESTION_RE = re.compile(
    "|".join(
        [
            r"\u4e00\u6761",  # one row
            r"\u968f\u673a",  # random
            r"\u968f\u4fbf",  # arbitrary
            r"\u4efb\u610f",  # any
            r"\u7b5b\u9009",  # filter/select
            r"\u5c55\u793a",  # show
            r"\u8be6\u7ec6",  # detail
            r"\u660e\u7ec6",  # detail
            r"\u8be6\u60c5",  # detail
            r"\u6837\u4f8b",  # sample
            r"sample",
            r"random",
        ]
    ),
    flags=re.IGNORECASE,
)

_NON_ASCII_ALIAS_RE = re.compile(
    r"\bAS\s+(`[^`\x00-\x7f]+`|\"[^\"\x00-\x7f]+\"|[^\s,)\x00-\x7f]+)",
    flags=re.IGNORECASE,
)


class Text2SQLGenerator:
    """Generate safe SELECT SQL for the configured datasource."""

    def __init__(self, llm_client=None):
        self.schema_manager = SchemaManager()
        self.validator = SQLValidator()
        self._llm_client = llm_client

    async def generate(self, question: str) -> str:
        """Generate an executable SELECT SQL statement."""
        rule_based_sql = self._try_generate_rule_based_sql(question)
        if rule_based_sql:
            logger.info("Text2SQL rule-based: '{}' -> {}", question[:50], rule_based_sql[:100])
            self.validator.validate(rule_based_sql)
            return rule_based_sql

        client = self._llm_client or get_llm_client()
        prompt = self._build_prompt(question, include_samples=True)

        try:
            response = await client.chat(
                [{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=1024,
            )
        except LLMError as e:
            msg = str(e)
            if "inappropriate" in msg.lower():
                logger.info("Schema with samples was rejected; retrying with lean schema")
                try:
                    response = await client.chat(
                        [{"role": "user", "content": self._build_prompt(question, include_samples=False)}],
                        temperature=0.0,
                        max_tokens=1024,
                    )
                except LLMError as e2:
                    raise SQLError(f"Text2SQL generation failed: {e2}") from e2
            else:
                raise SQLError(f"Text2SQL generation failed: {e}") from e

        sql = self._extract_sql(response)
        logger.info("Text2SQL: '{}' -> {}", question[:50], sql[:100])

        self.validator.validate(sql)
        return sql

    def _build_prompt(self, question: str, include_samples: bool = True) -> str:
        """Build the Text2SQL prompt."""
        return _TEXT2SQL_PROMPT.format(
            db_schema=self.schema_manager.get_schema_prompt(include_samples=include_samples),
            join_hints=self.schema_manager.get_join_hints(),
            dialect_guidance=self._get_dialect_guidance(),
            question=question,
        )

    def _extract_sql(self, response: str) -> str:
        """Extract a single SELECT statement from an LLM response."""
        text = response.strip()

        code_match = re.search(r"```(?:sql)?\s*(.*?)\s*```", text, flags=re.IGNORECASE | re.DOTALL)
        if code_match:
            text = code_match.group(1).strip()

        select_match = re.search(r"\bSELECT\b[\s\S]*", text, flags=re.IGNORECASE)
        if not select_match:
            raise SQLError(f"Text2SQL did not generate a SELECT statement: {response[:120]}")

        sql = select_match.group(0).strip()
        sql = re.split(r";|\n\s*(?:explanation|note|result|sql)\s*[:：]", sql, maxsplit=1)[0].strip()
        sql = self._normalize_sql(sql)
        return sql.rstrip(";")

    def _try_generate_rule_based_sql(self, question: str) -> str | None:
        """Handle common deterministic table requests without involving the LLM."""
        tables = self.schema_manager.get_table_list()
        mentioned = [table for table in tables if table in question]
        if len(mentioned) != 1:
            return None

        table = self._quote_identifier(mentioned[0])
        if _COUNT_QUESTION_RE.search(question):
            return f"SELECT COUNT(*) AS total_count FROM {table} LIMIT 100"

        if _SAMPLE_ROW_QUESTION_RE.search(question):
            order_expr = self._random_order_expression()
            if order_expr:
                return f"SELECT * FROM {table} ORDER BY {order_expr} LIMIT 1"
            return f"SELECT * FROM {table} LIMIT 1"

        return None

    def _get_dialect_guidance(self) -> str:
        dialect = self._get_dialect()
        return (
            "\nDialect requirements:\n"
            f"- Current datasource dialect: {dialect}\n"
            "- Output exactly one SELECT SQL statement only.\n"
            "- Use only schema tables/columns from the current datasource.\n"
            "- Aliases must be ASCII snake_case. Never use Chinese aliases like data_count or row_count in Chinese text.\n"
            "- Quote identifiers with backticks for MySQL/ClickHouse, and double quotes for SQLite.\n"
            "- For ClickHouse, avoid MySQL-only DATE_SUB syntax; use now(), today(), or INTERVAL syntax.\n"
        )

    def _get_dialect(self) -> str:
        try:
            return self.schema_manager._get_datasource().dialect_name
        except Exception:
            return "mysql"

    def _quote_identifier(self, identifier: str) -> str:
        quote = '"' if self._get_dialect() == "sqlite" else "`"
        escaped = identifier.replace(quote, quote + quote)
        return f"{quote}{escaped}{quote}"

    def _random_order_expression(self) -> str:
        dialect = self._get_dialect()
        if dialect == "clickhouse":
            return "rand()"
        if dialect == "mysql":
            return "RAND()"
        if dialect == "sqlite":
            return "RANDOM()"
        return ""

    def _normalize_sql(self, sql: str) -> str:
        """Normalize LLM SQL so ClickHouse/MySQL do not receive non-ASCII aliases."""
        alias_map = {
            "\u603b\u8bb0\u5f55\u6570": "total_count",  # 总记录数
            "\u6570\u636e\u6761\u6570": "total_count",  # 数据条数
            "\u8bb0\u5f55\u6570": "row_count",  # 记录数
            "\u6761\u6570": "row_count",  # 条数
            "\u6570\u91cf": "count_value",  # 数量
            "\u603b\u6570": "total_count",  # 总数
        }
        for zh_alias, ascii_alias in alias_map.items():
            sql = re.sub(
                rf"\bAS\s+[`\"]?{re.escape(zh_alias)}[`\"]?",
                f"AS {ascii_alias}",
                sql,
                flags=re.IGNORECASE,
            )

        return _NON_ASCII_ALIAS_RE.sub("AS value", sql)
