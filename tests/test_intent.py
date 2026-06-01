"""意图分类器测试"""
import sys
import types
from pathlib import Path

import pytest

if "loguru" not in sys.modules:
    logger = types.SimpleNamespace(
        info=lambda *args, **kwargs: None,
        warning=lambda *args, **kwargs: None,
        exception=lambda *args, **kwargs: None,
    )
    sys.modules["loguru"] = types.SimpleNamespace(logger=logger)

if "openai" not in sys.modules:
    sys.modules["openai"] = types.SimpleNamespace(AsyncOpenAI=object)

settings_stub = types.SimpleNamespace(
    deepseek_api_key="",
    deepseek_base_url="",
    deepseek_model="",
    dashscope_api_key="",
    bailian_model="",
    llm_temperature=0.1,
    llm_max_tokens=256,
)
settings_module = types.SimpleNamespace(settings=settings_stub, PROJECT_ROOT=Path(__file__).resolve().parents[1])
sys.modules.setdefault("config.settings", settings_module)

from tests.conftest import TEST_QUERIES
from ops_agent.core.intent.classifier import IntentClassifier
from ops_agent.core.intent.types import IntentType


class TestIntentClassifier:
    def setup_method(self):
        self.classifier = IntentClassifier()

    @pytest.mark.parametrize("query,expected_intent", TEST_QUERIES)
    def test_intent_classification(self, query, expected_intent):
        """测试意图分类准确率"""
        result = self.classifier._rule_classify(query.lower())
        actual = result.intent.value
        assert actual == expected_intent, f"'{query}': 期望 {expected_intent}，实际 {actual}"

    def test_all_intent_types_covered(self):
        """确保三种意图类型都能被识别"""
        queries = [
            ("如何安装nginx", IntentType.KNOWLEDGE_QUERY),
            ("有几台服务器", IntentType.DATA_ANALYSIS),
            ("web-01服务挂了", IntentType.FAULT_TROUBLESHOOTING),
        ]
        for query, expected in queries:
            result = self.classifier._rule_classify(query)
            assert result.intent == expected

    def test_entity_extraction(self):
        """测试实体提取"""
        query = "web-01服务器192.168.1.10中nginx服务CPU使用率100%"
        result = self.classifier._rule_classify(query.lower())
        entities = result.entities
        assert "192.168.1.10" in entities.get("ip", [])
        assert "web-01" in entities.get("hostname", [])
        assert "nginx" in entities.get("service", [])

    def test_confidence_range(self):
        """测试置信度范围"""
        result = self.classifier._rule_classify("如何重启nginx")
        assert 0 <= result.confidence <= 1.0

    def test_log_filename_analysis_is_fault_troubleshooting(self):
        """日志文件分析请求不应被下划线文件名误判为数据分析"""
        result = self.classifier._rule_classify("帮我分析一下ops_agent_2026-05-25.log文件")

        assert result.intent == IntentType.FAULT_TROUBLESHOOTING

    @pytest.mark.parametrize("query", [
        "please analyze ops_agent_2026-05-25.log file",
        "check error.log errors",
        "analyze /var/log/nginx/access.log",
    ])
    def test_log_file_questions_are_fault_troubleshooting(self, query):
        result = self.classifier._rule_classify(query.lower())

        assert result.intent == IntentType.FAULT_TROUBLESHOOTING
