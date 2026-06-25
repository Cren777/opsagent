import sys
import types

from ops_agent.api.services import llm_factory


class FakeUnifiedLLMClient:
    def __init__(self, engines):
        self.engines = engines


class FakeOpenAICompatibleEngine:
    def __init__(self, api_key="", base_url="", model_name=""):
        self.api_key = api_key
        self.base_url = base_url
        self.model_name = model_name


class FakeDashScopeSdkEngine:
    def __init__(self, api_key="", model_name=""):
        self.api_key = api_key
        self.model_name = model_name


def test_dashscope_provider_uses_configured_compatible_base_url(monkeypatch):
    fake_config_service = types.ModuleType("ops_agent.api.services.config_service")
    fake_config_service.list_llm_providers = lambda: [
        {
            "provider_type": "dashscope",
            "api_key": "dashscope-key",
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "model": "qwen3.7-plus",
            "is_primary": True,
        }
    ]

    fake_llm_client = types.ModuleType("ops_agent.models.llm.client")
    fake_llm_client.UnifiedLLMClient = FakeUnifiedLLMClient
    fake_llm_client.DeepSeekEngine = FakeOpenAICompatibleEngine
    fake_llm_client.BailianEngine = FakeDashScopeSdkEngine

    monkeypatch.setitem(sys.modules, "ops_agent.api.services.config_service", fake_config_service)
    monkeypatch.setitem(sys.modules, "ops_agent.models.llm.client", fake_llm_client)

    dynamic_client = llm_factory.get_dynamic_llm_client()

    assert len(dynamic_client.engines) == 1
    engine = dynamic_client.engines[0]
    assert isinstance(engine, FakeOpenAICompatibleEngine)
    assert engine.api_key == "dashscope-key"
    assert engine.base_url == "https://dashscope.aliyuncs.com/compatible-mode/v1"
    assert engine.model_name == "qwen3.7-plus"