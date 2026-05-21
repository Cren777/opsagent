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
            conn = pymysql.connect(
                host=config.get("host", "127.0.0.1"),
                port=config.get("port", 3306),
                user=config.get("user", ""),
                password=config.get("password", ""),
                database=config.get("database", ""),
                charset=config.get("charset", "utf8mb4"),
                connect_timeout=5,
            )
            conn.ping()
            conn.close()
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
