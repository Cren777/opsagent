import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    # --- LLM ---
    deepseek_api_key: str = os.getenv("DEEPSEEK_API_KEY", "")
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"

    dashscope_api_key: str = os.getenv("DASHSCOPE_API_KEY", "")
    bailian_model: str = "qwen-plus"

    llm_temperature: float = 0.1
    llm_max_tokens: int = 4096

    # --- Embedding ---
    embedding_model_name: str = "BAAI/bge-large-zh-v1.5"
    embedding_device: str = os.getenv("EMBEDDING_DEVICE", "cuda:0")
    embedding_dim: int = 1024

    # --- Runtime Config ---
    config_db_path: str = str(PROJECT_ROOT / "data" / "app_config.db")
    config_encryption_key: str = os.getenv("OPSAGENT_API_KEY", "demo-key")

    # --- Milvus ---
    milvus_db_path: str = str(PROJECT_ROOT / "data" / "vectors" / "milvus.db")
    milvus_knowledge_collection: str = "ops_knowledge"
    milvus_logs_collection: str = "ops_logs"

    # --- MySQL ---
    mysql_host: str = os.getenv("MYSQL_HOST", "127.0.0.1")
    mysql_port: int = int(os.getenv("MYSQL_PORT", "3306"))
    mysql_user: str = os.getenv("MYSQL_USER", "opsagent")
    mysql_password: str = os.getenv("MYSQL_PASSWORD", "opsagent123")
    mysql_database: str = os.getenv("MYSQL_DATABASE", "ops_agent")
    mysql_charset: str = "utf8mb4"

    @property
    def mysql_url(self) -> str:
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
            f"?charset={self.mysql_charset}"
        )

    # --- RAG ---
    rag_chunk_size: int = 512
    rag_chunk_overlap: int = 50
    rag_top_k: int = 5

    # --- Scripts ---
    approved_scripts_dir: str = str(PROJECT_ROOT / "scripts" / "approved")
    script_timeout: int = 30
    script_output_max_chars: int = 5000

    # --- Troubleshooting uploads and memory ---
    uploaded_logs_dir: str = str(PROJECT_ROOT / "data" / "uploads" / "logs")
    incident_cases_db_path: str = str(PROJECT_ROOT / "data" / "incident_cases.db")

    # --- Server ---
    host: str = "0.0.0.0"
    port: int = 8080
    debug: bool = True

    # --- Security ---
    api_key: str = os.getenv("OPSAGENT_API_KEY", "demo-key")
    auth_jwt_secret: str = os.getenv("OPSAGENT_AUTH_JWT_SECRET", os.getenv("OPSAGENT_API_KEY", "demo-key"))
    auth_token_expire_minutes: int = int(os.getenv("OPSAGENT_AUTH_TOKEN_EXPIRE_MINUTES", "1440"))

    model_config = {
        "env_file": ".env",
        "extra": "ignore",
    }


settings = Settings()

