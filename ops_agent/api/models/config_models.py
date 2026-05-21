"""SQLAlchemy ORM models for runtime configuration storage."""
from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, String, Boolean, Float, Integer, Text, DateTime
from sqlalchemy.orm import DeclarativeBase, Session
from config.settings import settings


class Base(DeclarativeBase):
    pass


class DataSourceConfigModel(Base):
    __tablename__ = "datasource_configs"

    id = Column(String(36), primary_key=True)
    name = Column(String(128), nullable=False)
    type = Column(String(32), nullable=False)
    config_json = Column(Text, nullable=False)  # JSON-encoded, encrypted sensitive fields
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class LLMProviderConfigModel(Base):
    __tablename__ = "llm_provider_configs"

    id = Column(String(36), primary_key=True)
    name = Column(String(128), nullable=False)
    provider_type = Column(String(32), nullable=False)
    api_key_encrypted = Column(Text, nullable=False)
    base_url = Column(String(512), nullable=False)
    model = Column(String(128), nullable=False)
    temperature = Column(Float, default=0.1)
    max_tokens = Column(Integer, default=4096)
    is_primary = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


def init_config_db():
    """Initialize the config database and create tables if they don't exist."""
    db_path = settings.config_db_path
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    return engine


def get_config_session() -> Session:
    """Get a new session for the config database."""
    engine = create_engine(f"sqlite:///{settings.config_db_path}")
    return Session(engine)
