"""Configuration service: CRUD operations with encryption for sensitive fields."""
import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session
from cryptography.fernet import Fernet
from loguru import logger

from config.settings import settings
from ops_agent.api.models.config_models import (
    DataSourceConfigModel,
    LLMProviderConfigModel,
    init_config_db,
)

# Module-level engine singleton
_engine: Optional[Engine] = None


def _get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = create_engine(f"sqlite:///{settings.config_db_path}")
    return _engine


def _get_session() -> Session:
    return Session(_get_engine(), expire_on_commit=False)


def _get_fernet() -> Fernet:
    import base64
    import hashlib

    key = settings.config_encryption_key.encode()
    derived = hashlib.sha256(key).digest()
    fernet_key = base64.urlsafe_b64encode(derived)
    return Fernet(fernet_key)


def _encrypt(value: str) -> str:
    f = _get_fernet()
    return f.encrypt(value.encode()).decode()


def _decrypt(value: str) -> str:
    f = _get_fernet()
    return f.decrypt(value.encode()).decode()


# ── Data Source CRUD ──────────────────────────────────────────────


def list_datasources() -> list[dict]:
    with _get_session() as s:
        rows = s.query(DataSourceConfigModel).order_by(DataSourceConfigModel.created_at.desc()).all()
        return [_datasource_to_dict(r) for r in rows]


def get_datasource(ds_id: str) -> Optional[dict]:
    with _get_session() as s:
        row = s.query(DataSourceConfigModel).filter_by(id=ds_id).first()
        return _datasource_to_dict(row) if row else None


def create_datasource(data: dict) -> dict:
    ds_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    config_json = _encrypt_config_fields(data.get("config", {}), data.get("type", "mysql"))
    with _get_session() as s:
        model = DataSourceConfigModel(
            id=ds_id,
            name=data["name"],
            type=data["type"],
            config_json=json.dumps(config_json),
            is_active=data.get("is_active", False),
            created_at=now,
            updated_at=now,
        )
        if model.is_active:
            _deactivate_others(s, ds_id)
        s.add(model)
        s.commit()
        result = _datasource_to_dict(model)
    logger.info("Created datasource: {} ({})", data["name"], ds_id)
    return result


def update_datasource(ds_id: str, data: dict) -> Optional[dict]:
    with _get_session() as s:
        model = s.query(DataSourceConfigModel).filter_by(id=ds_id).first()
        if not model:
            return None
        model.name = data.get("name", model.name)
        model.type = data.get("type", model.type)
        if "config" in data:
            config_json = _encrypt_config_fields(data["config"], model.type)
            model.config_json = json.dumps(config_json)
        model.is_active = data.get("is_active", model.is_active)
        model.updated_at = datetime.now(timezone.utc)
        if model.is_active:
            _deactivate_others(s, ds_id)
        s.commit()
        result = _datasource_to_dict(model)
    logger.info("Updated datasource: {} ({})", model.name, ds_id)
    return result


def delete_datasource(ds_id: str) -> bool:
    with _get_session() as s:
        model = s.query(DataSourceConfigModel).filter_by(id=ds_id).first()
        if not model:
            return False
        s.delete(model)
        s.commit()
    logger.info("Deleted datasource: {}", ds_id)
    return True


def activate_datasource(ds_id: str) -> bool:
    with _get_session() as s:
        model = s.query(DataSourceConfigModel).filter_by(id=ds_id).first()
        if not model:
            return False
        _deactivate_others(s, ds_id)
        model.is_active = True
        model.updated_at = datetime.now(timezone.utc)
        s.commit()
    logger.info("Activated datasource: {}", ds_id)
    return True


def _deactivate_others(session: Session, exclude_id: str):
    session.query(DataSourceConfigModel).filter(
        DataSourceConfigModel.id != exclude_id,
        DataSourceConfigModel.is_active == True,
    ).update({"is_active": False})


def _datasource_to_dict(model: DataSourceConfigModel) -> dict:
    config = json.loads(model.config_json)
    if "password" in config:
        config["password"] = _decrypt(config["password"])
    return {
        "id": model.id,
        "name": model.name,
        "type": model.type,
        "is_active": model.is_active,
        "config": config,
        "created_at": model.created_at if isinstance(model.created_at, str) else model.created_at.isoformat(),
        "updated_at": model.updated_at if isinstance(model.updated_at, str) else model.updated_at.isoformat(),
    }


def _encrypt_config_fields(config: dict, ds_type: str) -> dict:
    result = dict(config)
    if "password" in result and result["password"]:
        result["password"] = _encrypt(result["password"])
    if ds_type == "mysql" and "charset" not in result:
        result["charset"] = "utf8mb4"
    return result


# ── LLM Provider CRUD ─────────────────────────────────────────────


def list_llm_providers() -> list[dict]:
    with _get_session() as s:
        rows = s.query(LLMProviderConfigModel).order_by(LLMProviderConfigModel.created_at.desc()).all()
        return [_llm_to_dict(r) for r in rows]


def get_llm_provider(prov_id: str) -> Optional[dict]:
    with _get_session() as s:
        row = s.query(LLMProviderConfigModel).filter_by(id=prov_id).first()
        return _llm_to_dict(row) if row else None


def create_llm_provider(data: dict) -> dict:
    prov_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    api_key = data.get("api_key", "")
    with _get_session() as s:
        model = LLMProviderConfigModel(
            id=prov_id,
            name=data["name"],
            provider_type=data.get("provider_type", "openai_compatible"),
            api_key_encrypted=_encrypt(api_key) if api_key else "",
            base_url=data.get("base_url", ""),
            model=data.get("model", ""),
            temperature=data.get("temperature", 0.1),
            max_tokens=data.get("max_tokens", 4096),
            is_primary=data.get("is_primary", False),
            created_at=now,
            updated_at=now,
        )
        if model.is_primary:
            _deactivate_llm_primary(s, prov_id)
        s.add(model)
        s.commit()
        result = _llm_to_dict(model)
    logger.info("Created LLM provider: {} ({})", data["name"], prov_id)
    return result


def update_llm_provider(prov_id: str, data: dict) -> Optional[dict]:
    with _get_session() as s:
        model = s.query(LLMProviderConfigModel).filter_by(id=prov_id).first()
        if not model:
            return None
        model.name = data.get("name", model.name)
        model.provider_type = data.get("provider_type", model.provider_type)
        if data.get("api_key"):
            model.api_key_encrypted = _encrypt(data["api_key"])
        if "base_url" in data:
            model.base_url = data["base_url"]
        if "model" in data:
            model.model = data["model"]
        if "temperature" in data:
            model.temperature = data["temperature"]
        if "max_tokens" in data:
            model.max_tokens = data["max_tokens"]
        model.is_primary = data.get("is_primary", model.is_primary)
        model.updated_at = datetime.now(timezone.utc)
        if model.is_primary:
            _deactivate_llm_primary(s, prov_id)
        s.commit()
        result = _llm_to_dict(model)
    logger.info("Updated LLM provider: {} ({})", model.name, prov_id)
    return result


def delete_llm_provider(prov_id: str) -> bool:
    with _get_session() as s:
        model = s.query(LLMProviderConfigModel).filter_by(id=prov_id).first()
        if not model:
            return False
        s.delete(model)
        s.commit()
    logger.info("Deleted LLM provider: {}", prov_id)
    return True


def set_primary_llm(prov_id: str) -> bool:
    with _get_session() as s:
        model = s.query(LLMProviderConfigModel).filter_by(id=prov_id).first()
        if not model:
            return False
        _deactivate_llm_primary(s, prov_id)
        model.is_primary = True
        model.updated_at = datetime.now(timezone.utc)
        s.commit()
    logger.info("Set primary LLM: {}", prov_id)
    return True


def _deactivate_llm_primary(session: Session, exclude_id: str):
    session.query(LLMProviderConfigModel).filter(
        LLMProviderConfigModel.id != exclude_id,
        LLMProviderConfigModel.is_primary == True,
    ).update({"is_primary": False})


def _llm_to_dict(model: LLMProviderConfigModel) -> dict:
    api_key = ""
    if model.api_key_encrypted:
        try:
            api_key = _decrypt(model.api_key_encrypted)
        except Exception:
            pass
    return {
        "id": model.id,
        "name": model.name,
        "provider_type": model.provider_type,
        "base_url": model.base_url,
        "model": model.model,
        "temperature": model.temperature,
        "max_tokens": model.max_tokens,
        "is_primary": model.is_primary,
        "api_key": api_key,
        "created_at": model.created_at if isinstance(model.created_at, str) else model.created_at.isoformat(),
        "updated_at": model.updated_at if isinstance(model.updated_at, str) else model.updated_at.isoformat(),
    }


# ── Initialization ────────────────────────────────────────────────


def seed_default_configs():
    """Seed config DB with defaults from settings/.env if empty."""
    with _get_session() as s:
        ds_count = s.query(DataSourceConfigModel).count()
        llm_count = s.query(LLMProviderConfigModel).count()

    if ds_count == 0 and settings.mysql_host:
        try:
            create_datasource({
                "name": "MySQL (默认)",
                "type": "mysql",
                "is_active": True,
                "config": {
                    "host": settings.mysql_host,
                    "port": settings.mysql_port,
                    "user": settings.mysql_user,
                    "password": settings.mysql_password,
                    "database": settings.mysql_database,
                    "charset": settings.mysql_charset,
                },
            })
            logger.info("Seeded default MySQL datasource")
        except Exception as e:
            logger.warning("Failed to seed default datasource: {}", e)

    if llm_count == 0:
        if settings.deepseek_api_key and "your-" not in settings.deepseek_api_key:
            try:
                create_llm_provider({
                    "name": "DeepSeek",
                    "provider_type": "openai_compatible",
                    "api_key": settings.deepseek_api_key,
                    "base_url": settings.deepseek_base_url,
                    "model": settings.deepseek_model,
                    "temperature": settings.llm_temperature,
                    "max_tokens": settings.llm_max_tokens,
                    "is_primary": True,
                })
                logger.info("Seeded default DeepSeek LLM provider")
            except Exception as e:
                logger.warning("Failed to seed DeepSeek provider: {}", e)
        if settings.dashscope_api_key and "your-" not in settings.dashscope_api_key:
            try:
                create_llm_provider({
                    "name": "阿里百炼 (Qwen)",
                    "provider_type": "dashscope",
                    "api_key": settings.dashscope_api_key,
                    "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                    "model": settings.bailian_model,
                    "temperature": settings.llm_temperature,
                    "max_tokens": settings.llm_max_tokens,
                    "is_primary": False,
                })
                logger.info("Seeded default Bailian LLM provider")
            except Exception as e:
                logger.warning("Failed to seed Bailian provider: {}", e)


# Initialize on module load
init_config_db()
