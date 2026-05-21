"""意图分类器测试"""
import pytest
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
