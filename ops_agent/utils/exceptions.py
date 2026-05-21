class OpsAgentError(Exception):
    """基础异常类"""


class LLMError(OpsAgentError):
    """LLM 调用异常"""


class LLMTimeoutError(LLMError):
    """LLM 调用超时"""


class LLMAuthError(LLMError):
    """LLM 认证失败"""


class DatabaseError(OpsAgentError):
    """数据库操作异常"""


class DatabaseConnectionError(DatabaseError):
    """数据库连接失败"""


class SQLError(DatabaseError):
    """SQL 执行异常"""


class DangerousSQLError(SQLError):
    """危险 SQL 操作被拦截"""


class VectorStoreError(OpsAgentError):
    """向量数据库异常"""


class DocumentLoadError(OpsAgentError):
    """文档加载异常"""


class ScriptExecutionError(OpsAgentError):
    """脚本执行异常"""


class ScriptTimeoutError(ScriptExecutionError):
    """脚本执行超时"""


class InvalidIntentError(OpsAgentError):
    """无效意图"""
