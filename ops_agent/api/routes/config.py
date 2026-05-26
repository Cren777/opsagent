"""Configuration API routes for data sources and LLM providers."""
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ops_agent.api.services import config_service

router = APIRouter(prefix="/api/config", tags=["配置管理"])


# ── Pydantic Schemas ──────────────────────────────────────────────

class DataSourceConfigSchema(BaseModel):
    host: Optional[str] = None
    port: Optional[int] = None
    user: Optional[str] = None
    password: Optional[str] = None
    database: Optional[str] = None
    charset: Optional[str] = None
    file_path: Optional[str] = None
    sheet_name: Optional[str] = None
    selected_tables: Optional[list[str]] = None
    all_tables: Optional[list[str]] = None
    total_tables: Optional[int] = None


class DataSourceCreate(BaseModel):
    name: str
    type: str  # mysql, clickhouse, excel_csv
    config: DataSourceConfigSchema
    is_active: bool = False


class DataSourceUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    config: Optional[DataSourceConfigSchema] = None
    is_active: Optional[bool] = None


class LLMProviderCreate(BaseModel):
    name: str
    provider_type: str = "openai_compatible"
    api_key: str = ""
    base_url: str = ""
    model: str = ""
    temperature: float = 0.1
    max_tokens: int = 4096
    is_primary: bool = False


class LLMProviderUpdate(BaseModel):
    name: Optional[str] = None
    provider_type: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    is_primary: Optional[bool] = None


# ── Data Source Endpoints ─────────────────────────────────────────


@router.get("/datasources")
def list_datasources():
    return config_service.list_datasources()


@router.post("/datasources")
def create_datasource(data: DataSourceCreate):
    return config_service.create_datasource(data.model_dump(exclude_none=True))


@router.put("/datasources/{ds_id}")
def update_datasource(ds_id: str, data: DataSourceUpdate):
    result = config_service.update_datasource(ds_id, data.model_dump(exclude_none=True))
    if not result:
        raise HTTPException(404, "数据源不存在")
    return result


@router.delete("/datasources/{ds_id}")
def delete_datasource(ds_id: str):
    if not config_service.delete_datasource(ds_id):
        raise HTTPException(404, "数据源不存在")
    return {"ok": True}


@router.post("/datasources/{ds_id}/activate")
def activate_datasource(ds_id: str):
    if not config_service.activate_datasource(ds_id):
        raise HTTPException(404, "数据源不存在")
    return {"ok": True}


@router.post("/datasources/{ds_id}/test")
def test_datasource(ds_id: str):
    """Test connection to a saved datasource."""
    ds = config_service.get_datasource(ds_id)
    if not ds:
        raise HTTPException(404, "数据源不存在")
    return _test_connection(ds["type"], ds["config"])


class TablesForNewDataSource(BaseModel):
    type: str
    config: DataSourceConfigSchema


@router.post("/datasources/tables")
def list_new_datasource_tables(data: TablesForNewDataSource):
    """List tables for an unsaved connection config."""
    return _list_tables(data.type, data.config.model_dump(exclude_none=True))


@router.get("/datasources/{ds_id}/tables")
def list_datasource_tables(ds_id: str):
    """List tables for a saved datasource."""
    ds = config_service.get_datasource(ds_id)
    if not ds:
        raise HTTPException(404, "数据源不存在")
    return _list_tables(ds["type"], ds["config"])


def _list_tables(ds_type: str, config: dict) -> dict:
    """Helper to get table list from a datasource config."""
    try:
        if ds_type == "mysql":
            from ops_agent.models.tools.mysql_source import MySQLDataSource
            ds = MySQLDataSource(config)
        elif ds_type == "clickhouse":
            from ops_agent.models.tools.clickhouse_source import ClickHouseDataSource
            ds = ClickHouseDataSource(config)
        elif ds_type == "excel_csv":
            return {"tables": []}
        else:
            return {"tables": []}
        tables = ds.get_tables()
        return {"tables": tables}
    except Exception as e:
        raise HTTPException(400, f"获取表列表失败: {e}")


@router.post("/datasources/test")
def test_new_datasource(data: DataSourceCreate):
    """Test connection with provided config (no save)."""
    return _test_connection(data.type, data.config.model_dump(exclude_none=True))


def _test_connection(ds_type: str, config: dict) -> dict:
    import time
    start = time.time()
    try:
        if ds_type == "mysql":
            import pymysql
            try:
                conn = pymysql.connect(
                    host=config.get("host", "127.0.0.1"),
                    port=config.get("port", 3306),
                    user=config.get("user", ""),
                    password=config.get("password", ""),
                    database=config.get("database", ""),
                    charset=config.get("charset", "utf8mb4"),
                    connect_timeout=10,
                    read_timeout=10,
                    write_timeout=10,
                )
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                conn.close()
            except pymysql.err.OperationalError as e:
                return {"ok": False, "message": _format_mysql_operational_error(e, config)}
        elif ds_type == "clickhouse":
            from clickhouse_connect import get_client
            client = get_client(
                host=config.get("host", "127.0.0.1"),
                port=config.get("port", 8123),
                username=config.get("user", ""),
                password=config.get("password", ""),
                database=config.get("database", "default"),
                connect_timeout=5,
            )
            client.command("SELECT 1")
        elif ds_type == "excel_csv":
            import os
            file_path = config.get("file_path", "")
            if not os.path.exists(file_path):
                return {"ok": False, "message": f"文件不存在: {file_path}"}
            return {"ok": True, "message": "文件存在，可读取"}
        else:
            return {"ok": False, "message": f"不支持的数据源类型: {ds_type}"}

        latency = (time.time() - start) * 1000
        return {"ok": True, "message": "连接成功", "latency_ms": round(latency, 1)}
    except ImportError as e:
        return {"ok": False, "message": f"缺少驱动: {e}"}
    except Exception as e:
        return {"ok": False, "message": str(e)}


def _format_mysql_operational_error(error: Exception, config: dict) -> str:
    code = error.args[0] if getattr(error, "args", None) else None
    host = config.get("host", "127.0.0.1")
    port = config.get("port", 3306)
    database = config.get("database", "")
    raw = str(error)

    messages = {
        2003: (
            f"OpsAgent 后端无法连接 MySQL 服务器 {host}:{port}。"
            "请确认 MySQL 服务器防火墙/安全组已放行 OpsAgent 后端服务器 IP，"
            "并确认 mysqld 已监听该地址和端口。"
        ),
        1045: (
            f"MySQL 用户认证失败。请确认用户名/密码正确，并确认该用户允许 OpsAgent 后端服务器 IP 登录。"
        ),
        1049: f"MySQL 数据库不存在：{database}。",
        2005: f"MySQL 主机地址无法解析：{host}。",
        2013: "MySQL 连接已建立但通信中断，请检查网络稳定性或 MySQL 超时配置。",
    }
    detail = messages.get(code, "MySQL 连接测试失败。")
    return f"{detail} 原始错误：{raw}"


# ── LLM Provider Endpoints ────────────────────────────────────────


@router.get("/llm")
def list_llm_providers():
    return config_service.list_llm_providers()


@router.post("/llm")
def create_llm_provider(data: LLMProviderCreate):
    return config_service.create_llm_provider(data.model_dump(exclude_none=True))


@router.put("/llm/{prov_id}")
def update_llm_provider(prov_id: str, data: LLMProviderUpdate):
    result = config_service.update_llm_provider(prov_id, data.model_dump(exclude_none=True))
    if not result:
        raise HTTPException(404, "大模型提供商不存在")
    return result


@router.delete("/llm/{prov_id}")
def delete_llm_provider(prov_id: str):
    if not config_service.delete_llm_provider(prov_id):
        raise HTTPException(404, "大模型提供商不存在")
    return {"ok": True}


@router.post("/llm/{prov_id}/primary")
def set_primary_llm(prov_id: str):
    if not config_service.set_primary_llm(prov_id):
        raise HTTPException(404, "大模型提供商不存在")
    return {"ok": True}


class TestLLMRequest(BaseModel):
    message: str = "你好，请简要介绍一下你自己。"


@router.post("/llm/{prov_id}/test")
def test_llm_provider(prov_id: str, req: TestLLMRequest):
    """Test a saved LLM provider with a chat message."""
    prov = config_service.get_llm_provider(prov_id)
    if not prov:
        raise HTTPException(404, "大模型提供商不存在")
    return _test_llm_chat(prov, req.message)


class TestNewLLMRequest(BaseModel):
    name: str = ""
    provider_type: str = "openai_compatible"
    api_key: str = ""
    base_url: str = ""
    model: str = ""
    temperature: float = 0.1
    max_tokens: int = 4096
    message: str = "你好，请简要介绍一下你自己。"


@router.post("/llm/test")
def test_new_llm_provider(data: TestNewLLMRequest):
    """Test a new LLM provider (not saved) with a chat message."""
    return _test_llm_chat(data.model_dump(), data.message)


def _test_llm_chat(prov: dict, message: str) -> dict:
    import time
    start = time.time()
    try:
        api_key = prov.get("api_key", "") or prov.get("api_key_encrypted", "")
        if not api_key:
            return {"response": "", "latency_ms": 0, "error": "API Key 未配置"}

        base_url = prov.get("base_url", "")
        model = prov.get("model", "")
        provider_type = prov.get("provider_type", "openai_compatible")

        if provider_type == "dashscope":
            return _test_dashscope(api_key, model, message, start)
        else:
            return _test_openai_compatible(api_key, base_url, model, message, start)
    except Exception as e:
        return {"response": "", "latency_ms": round((time.time() - start) * 1000, 1), "error": str(e)}


def _test_openai_compatible(api_key: str, base_url: str, model: str, message: str, start: float) -> dict:
    import requests
    resp = requests.post(
        f"{base_url.rstrip('/')}/chat/completions",
        json={
            "model": model,
            "messages": [{"role": "user", "content": message}],
            "max_tokens": 256,
        },
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    content = data["choices"][0]["message"]["content"]
    latency = (time.time() - start) * 1000
    return {"response": content, "latency_ms": round(latency, 1)}


def _test_dashscope(api_key: str, model: str, message: str, start: float) -> dict:
    import requests
    resp = requests.post(
        "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        json={
            "model": model,
            "messages": [{"role": "user", "content": message}],
            "max_tokens": 256,
        },
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    content = data["choices"][0]["message"]["content"]
    latency = (time.time() - start) * 1000
    return {"response": content, "latency_ms": round(latency, 1)}
