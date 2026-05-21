"""任务路由器：意图 → 处理器映射"""
from typing import Dict, Any
from loguru import logger

from ops_agent.core.intent.types import IntentType


class TaskRouter:
    """根据意图类型路由到对应处理器"""

    def __init__(self):
        self._handlers: Dict[IntentType, callable] = {}

    def register(self, intent: IntentType, handler: callable):
        """注册意图处理器"""
        self._handlers[intent] = handler
        logger.info("注册处理器: {} → {}", intent, handler.__name__)

    async def route(self, intent: IntentType, query: str, entities: Dict[str, Any] = None) -> Dict[str, Any]:
        """路由到对应处理器并执行"""
        entities = entities or {}
        handler = self._handlers.get(intent)
        if handler is None:
            logger.warning("未找到意图 {} 的处理器，使用知识查询兜底", intent)
            handler = self._handlers.get(IntentType.KNOWLEDGE_QUERY)

        if handler is None:
            return {"answer": "抱歉，系统未配置任何处理器。", "type": "error"}

        logger.info("路由: {} → {}", intent, handler.__name__)
        result = await handler(query, entities)
        result["intent"] = intent
        return result
