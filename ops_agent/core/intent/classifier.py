"""意图分类器：规则快速通道 + LLM 精准分类"""
import re
import json
from typing import Optional
from loguru import logger

from ops_agent.core.intent.types import IntentType, IntentResult
from ops_agent.models.llm.client import get_llm_client, UnifiedLLMClient, LLMError
from config.settings import settings


_DATA_QUERY_HINT_RE = re.compile(
    "|".join(
        [
            r"\bselect\b",
            r"\bfrom\b",
            r"\blimit\b",
            r"[a-z][a-z0-9]*_[a-z0-9_]+",
            r"\u8868.*(\u4e00\u6761|\u968f\u673a|\u968f\u4fbf|\u7b5b\u9009|\u5c55\u793a|\u8be6\u7ec6|\u660e\u7ec6|\u6570\u636e)",
            r"(\u4e00\u6761|\u968f\u673a|\u968f\u4fbf|\u7b5b\u9009|\u5c55\u793a|\u8be6\u7ec6|\u660e\u7ec6).*\u8868",
            r"(\u67e5\u8be2|\u7edf\u8ba1|\u663e\u793a|\u5217\u51fa).*(\u8868|\u6570\u636e|\u8bb0\u5f55)",
        ]
    ),
    re.IGNORECASE,
)


# 规则匹配模式
_RULE_PATTERNS = {
    IntentType.DATA_ANALYSIS: [
        r"(多少|几个|哪些|几台|有几|查询|统计|汇总|列出|显示).*(告警|工单|服务器|服务|用户|指标|数据)",
        r"(最近|过去|近).*\d+.*(天|周|月|小时|分钟).*",
        r"(每个|各个|分组|按.*分).*",
        r"(平均|最大|最小|TOP|排名).*",
    ],
    IntentType.FAULT_TROUBLESHOOTING: [
        r"(故障|异常|报错|错误|排查|诊断|解决|恢复|down|挂了|crash|起不来|不行)",
        r"(CPU|内存|磁盘|网络).*(高|满|不足|不够|慢|卡|超|爆|100%|9\d%|8\d%)",
        r"(连接数|响应|超时|延迟|丢包|OOM|oom).*",
        r"(Permission denied|Connection refused|Out of memory|disk full|No space)",
    ],
    IntentType.KNOWLEDGE_QUERY: [
        r"(如何|怎么|怎样|如何做|怎么做|命令|步骤|处理|修复).*",
        r"(什么是|是什么|含义|定义).*",
        r"(查看|检查|确认|验证).*",
    ],
    IntentType.KNOWLEDGE_QUERY: [
        r"(如何|怎么|怎样|如何做|怎么做|命令|步骤).*",
        r"(什么是|是什么|含义|定义).*",
        r"(查看|检查|确认|验证).*",
    ],
}

_ENTITY_PATTERNS = {
    "ip": r"(?<!\d)(?:\d{1,3}\.){3}\d{1,3}(?!\d)",
    "hostname": r"(?<![a-z0-9])([a-z][a-z0-9]*-\d{2}|db-master|db-slave-\d|web-\d{2}|app-\d{2}|cache-\d{2}|mq-\d{2}|monitor-\d{2}|log-\d{2}|dns-\d{2}|lb-\d{2}|dev-\d{2})(?![a-z0-9])",
    "service": r"(?<![a-z])(nginx|mysql|redis|rabbitmq|tomcat|docker|k8s|haproxy|prometheus|grafana|elasticsearch|kibana|logstash|jenkins|gitlab)(?![a-z])",
    "port": r":(\d{1,5})\b",
}

_INTENT_CLASSIFY_PROMPT = """你是一个IT运维意图识别助手。请分析用户输入，判断意图类型并提取关键实体。

意图类型：
- knowledge_query: 查询运维知识、操作方法、命令用法
- data_analysis: 数据分析、统计查询、报表
- fault_troubleshooting: 故障排查、异常诊断、问题修复

请以JSON格式输出：
{
  "intent": "knowledge_query|data_analysis|fault_troubleshooting",
  "confidence": 0.0-1.0,
  "entities": {"ip": [], "hostname": [], "service": [], "other": []}
}

用户输入：{query}

JSON输出："""


class IntentClassifier:
    """两级意图分类器"""

    def __init__(self, llm_client: Optional[UnifiedLLMClient] = None):
        self._llm_client = llm_client

    async def classify(self, query: str) -> IntentResult:
        """分类用户查询意图"""
        query_lower = query.lower()

        # 一级：规则快速通道
        rule_result = self._rule_classify(query_lower)
        if rule_result.confidence >= 0.8:
            logger.info("规则分类: {} (置信度: {})", rule_result.intent, rule_result.confidence)
            return rule_result

        # 二级：LLM 精准分类
        try:
            llm_result = await self._llm_classify(query)
            logger.info("LLM分类: {} (置信度: {})", llm_result.intent, llm_result.confidence)
            return llm_result
        except Exception as e:
            logger.warning("LLM分类失败: {}，使用规则分类兜底", e)
            return rule_result

    ...

    def _rule_classify(self, query_lower: str) -> IntentResult:
        """基于规则的快速分类"""
        entities = self._extract_entities(query_lower)
        if _DATA_QUERY_HINT_RE.search(query_lower):
            return IntentResult(
                intent=IntentType.DATA_ANALYSIS,
                confidence=0.95,
                entities=entities,
                raw_query=query_lower,
            )

        scores = {intent: 0 for intent in IntentType}
        for intent, patterns in _RULE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    scores[intent] += 1

        if max(scores.values()) == 0:
            return IntentResult(
                intent=IntentType.KNOWLEDGE_QUERY,
                confidence=0.5,
                entities=entities,
                raw_query=query_lower,
            )

        # 打破平局：KNOWLEDGE_QUERY 优先（安全兜底）
        best = max(scores, key=lambda k: (scores[k], k == IntentType.KNOWLEDGE_QUERY))
        confidence = min(scores[best] / max(sum(scores.values()), 1), 1.0)
        return IntentResult(
            intent=best,
            confidence=round(confidence, 2),
            entities=entities,
            raw_query=query_lower,
        )

    def _get_client(self) -> UnifiedLLMClient:
        return self._llm_client or get_llm_client()

    async def _llm_classify(self, query: str) -> IntentResult:
        """LLM 精准分类"""
        client = self._get_client()
        prompt = _INTENT_CLASSIFY_PROMPT.format(query=query)
        messages = [{"role": "user", "content": prompt}]

        response_text = await client.chat(messages, temperature=0.0, max_tokens=256)
        response = self._extract_json(response_text)

        intent_str = response.get("intent", "knowledge_query")
        intent = IntentType.KNOWLEDGE_QUERY
        try:
            intent = IntentType(intent_str)
        except ValueError:
            pass

        confidence = float(response.get("confidence", 0.7))
        entities = response.get("entities", {})
        entities.update(self._extract_entities(query))

        return IntentResult(
            intent=intent,
            confidence=round(confidence, 2),
            entities=entities,
            raw_query=query,
        )

    def _extract_entities(self, query: str) -> dict:
        """提取实体（IP、主机名、服务名等）"""
        entities = {}
        for name, pattern in _ENTITY_PATTERNS.items():
            matches = re.findall(pattern, query, re.IGNORECASE)
            if matches:
                entities[name] = list(set(matches))
        return entities

    @staticmethod
    def _extract_json(text: str) -> dict:
        """从 LLM 输出中提取 JSON"""
        text = text.strip()
        # 尝试直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        # 尝试提取 ```json ... ``` 块
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        # 尝试提取第一个 {...} 块
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        return {"intent": "knowledge_query"}
