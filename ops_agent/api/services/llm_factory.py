"""Dynamic LLM client factory that reads providers from config DB."""
from typing import Optional
from loguru import logger


def get_dynamic_llm_client():
    """Create an LLM client from config DB providers, falling back to settings defaults."""
    try:
        from ops_agent.api.services.config_service import list_llm_providers
        providers = list_llm_providers()
    except Exception:
        providers = []

    if not providers:
        # Fallback to settings-based defaults
        from ops_agent.models.llm.client import get_llm_client
        logger.info("配置数据库中无 LLM 提供商，使用 settings 默认配置")
        return get_llm_client()

    # Build engines from config
    from ops_agent.models.llm.client import UnifiedLLMClient, DeepSeekEngine

    primary = next((p for p in providers if p.get("is_primary")), providers[0])
    engines = []

    for prov in providers:
        pk = prov.get("api_key", "") or prov.get("api_key_encrypted", "")
        if not pk:
            continue

        provider_type = prov.get("provider_type", "openai_compatible")

        if provider_type == "dashscope":
            engine = DeepSeekEngine(
                api_key=pk,
                base_url=prov.get("base_url") or "https://dashscope.aliyuncs.com/compatible-mode/v1",
                model_name=prov.get("model", "qwen-plus"),
            )
        else:
            engine = DeepSeekEngine(
                api_key=pk,
                base_url=prov.get("base_url", "https://api.deepseek.com"),
                model_name=prov.get("model", "deepseek-chat"),
            )
        engines.append(engine)

    if not engines:
        from ops_agent.models.llm.client import get_llm_client
        return get_llm_client()

    return UnifiedLLMClient(engines)
