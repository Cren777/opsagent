"""多源结果融合模块"""
import asyncio
from typing import Dict, Any, List
from loguru import logger

from typing import Optional
from ops_agent.models.llm.client import get_llm_client, UnifiedLLMClient


_FUSION_PROMPT = """你是一个IT运维专家。根据以下多源信息，对用户的问题给出专业的诊断结论。

## 用户问题
{question}

## 知识库检索结果
{knowledge_context}

## 数据库查询结果
{db_results}

## 系统诊断结果
{script_output}

## 相关日志
{log_context}

请按以下格式输出：
### 问题摘要
一句话描述

### 证据
来自上述数据源的关键证据

### 根因分析
分析问题的根本原因

### 解决方案
具体的解决步骤（按优先级排列）
"""

_QA_PROMPT = """你是一个IT运维专家，请根据以下参考文档回答用户的问题。

## 参考文档
{context}

## 用户问题
{question}

请给出准确、实用的回答。如果参考文档不足以回答问题，请如实说明。
"""

_DATA_QA_PROMPT = """你是一个IT数据分析师。请用自然语言总结以下数据库查询结果。

## 用户问题
{question}

## 查询结果
{results}

请用简洁易懂的中文总结，适当使用列表或表格格式。
"""


class ResponseFusion:
    """多源结果融合器"""

    def __init__(self, llm_client: Optional[UnifiedLLMClient] = None):
        self._llm_client = llm_client

    def _get_client(self) -> UnifiedLLMClient:
        return self._llm_client or get_llm_client()

    async def fuse_for_troubleshooting(
        self,
        question: str,
        knowledge_context: str,
        db_results: str,
        script_output: str,
        log_context: str,
    ) -> str:
        """故障排查结果融合"""
        prompt = _FUSION_PROMPT.format(
            question=question,
            knowledge_context=knowledge_context or "（无相关文档）",
            db_results=db_results or "（无数据库查询结果）",
            script_output=script_output or "（无系统诊断结果）",
            log_context=log_context or "（无相关日志）",
        )

        client = self._get_client()
        messages = [{"role": "user", "content": prompt}]
        return await client.chat(messages, temperature=0.3, max_tokens=2048)

    async def fuse_for_knowledge(self, question: str, context: str) -> str:
        """知识问答融合"""
        if not context:
            client = self._get_client()
            messages = [{"role": "user", "content": question}]
            return await client.chat(messages, temperature=0.3)

        prompt = _QA_PROMPT.format(question=question, context=context)
        client = self._get_client()
        messages = [{"role": "user", "content": prompt}]
        return await client.chat(messages, temperature=0.3)

    async def fuse_for_data(self, question: str, results: str) -> str:
        """数据分析结果总结"""
        prompt = _DATA_QA_PROMPT.format(question=question, results=results)
        client = self._get_client()
        messages = [{"role": "user", "content": prompt}]
        return await client.chat(messages, temperature=0.3, max_tokens=1024)
