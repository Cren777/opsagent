"""意图类型定义"""
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any


class IntentType(str, Enum):
    KNOWLEDGE_QUERY = "knowledge_query"        # 知识查询："如何重启nginx？"
    DATA_ANALYSIS = "data_analysis"             # 数据分析："最近24小时有多少告警？"
    FAULT_TROUBLESHOOTING = "fault_troubleshooting"  # 故障排查："CPU使用率100%"


@dataclass
class IntentResult:
    intent: IntentType
    confidence: float = 1.0
    entities: Dict[str, Any] = field(default_factory=dict)
    raw_query: str = ""
