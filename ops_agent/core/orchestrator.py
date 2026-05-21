"""核心编排器：意图分类 → 路由分发 → 结果融合 → 流式输出"""
import asyncio
from typing import AsyncGenerator, Dict, Any, Optional
from loguru import logger

from ops_agent.core.intent.types import IntentType
from ops_agent.core.intent.classifier import IntentClassifier
from ops_agent.core.scheduler.task_router import TaskRouter
from ops_agent.core.fusion.response_fusion import ResponseFusion
from ops_agent.models.llm.client import get_llm_client, UnifiedLLMClient
from ops_agent.models.rag.knowledge_base import get_knowledge_base
from ops_agent.models.rag.log_parser import LogIndexer
from ops_agent.models.text2sql.generator import Text2SQLGenerator
from ops_agent.models.tools.datasource_factory import get_active_datasource
from ops_agent.models.tools.script_executor import ScriptExecutor


class Orchestrator:
    """系统核心编排器"""

    def __init__(self, llm_client: Optional[UnifiedLLMClient] = None):
        self.classifier = IntentClassifier(llm_client)
        self.router = TaskRouter()
        self.fusion = ResponseFusion(llm_client)

        self.kb = get_knowledge_base()
        self.text2sql = Text2SQLGenerator()
        self.log_indexer = LogIndexer()
        self.script_executor = ScriptExecutor()

        self._register_handlers()

    def _register_handlers(self):
        """注册意图处理器"""
        self.router.register(IntentType.KNOWLEDGE_QUERY, self._handle_knowledge)
        self.router.register(IntentType.DATA_ANALYSIS, self._handle_data_analysis)
        self.router.register(IntentType.FAULT_TROUBLESHOOTING, self._handle_fault_troubleshooting)

    async def process(self, query: str) -> Dict[str, Any]:
        """非流式处理用户查询"""
        intent_result = await self.classifier.classify(query)
        result = await self.router.route(
            intent_result.intent,
            query,
            intent_result.entities,
        )
        result["intent"] = intent_result.intent.value
        return result

    async def process_stream(self, query: str) -> AsyncGenerator[Dict[str, Any], None]:
        """流式处理用户查询，通过 SSE 事件逐步返回"""
        # Step 1: 意图识别
        intent_result = await self.classifier.classify(query)
        yield {"event": "intent", "data": {"type": intent_result.intent.value}}

        # Step 2: 执行处理器
        result = await self.router.route(
            intent_result.intent,
            query,
            intent_result.entities,
        )

        # Step 3: 流式输出响应
        answer = result.get("answer", "抱歉，无法处理您的请求。")
        if len(answer) > 50:
            # 模拟 token-level streaming
            tokens = answer  # 完整文本
            chunk_size = 20
            for i in range(0, len(tokens), chunk_size):
                chunk = tokens[i:i + chunk_size]
                yield {"event": "token", "data": {"text": chunk}}
                await asyncio.sleep(0.01)  # 模拟逐字输出延迟
        else:
            yield {"event": "token", "data": {"text": answer}}

        # Step 4: 完成（附加元数据）
        yield {
            "event": "done",
            "data": {
                "intent": intent_result.intent.value,
                "sources": result.get("sources", []),
                "sql": result.get("sql", ""),
            }
        }

    async def _handle_knowledge(self, query: str, entities: dict) -> Dict[str, Any]:
        """处理知识查询"""
        context = self.kb.query(query)
        sources = self.kb.search(query, top_k=3)
        answer = await self.fusion.fuse_for_knowledge(query, context)
        return {
            "answer": answer,
            "sources": [{"title": s["title"], "file": s["source_file"]} for s in sources],
        }

    async def _handle_data_analysis(self, query: str, entities: dict) -> Dict[str, Any]:
        """处理数据分析查询"""
        ds = get_active_datasource()
        if ds is None:
            return {"answer": "错误：数据源未配置或连接失败，请在数据源配置页面检查。", "rows": []}
        sql = await self.text2sql.generate(query)
        rows = ds.execute_query(sql)
        results_text = self._format_rows(rows)
        answer = await self.fusion.fuse_for_data(query, results_text)
        return {
            "answer": answer,
            "sql": sql,
            "rows": rows,
        }

    async def _handle_fault_troubleshooting(self, query: str, entities: dict) -> Dict[str, Any]:
        """处理故障排查"""
        # 并行获取多源信息
        knowledge_task = asyncio.create_task(
            asyncio.to_thread(self.kb.query, query)
        )
        log_task = asyncio.create_task(
            asyncio.to_thread(self._search_logs, query, entities)
        )
        script_task = asyncio.create_task(
            asyncio.to_thread(self._run_diagnostics, entities)
        )

        knowledge_context = await knowledge_task
        log_context = await log_task
        script_output = await script_task

        answer = await self.fusion.fuse_for_troubleshooting(
            question=query,
            knowledge_context=knowledge_context,
            db_results="",
            script_output=script_output,
            log_context=log_context,
        )

        return {"answer": answer}

    def _search_logs(self, query: str, entities: dict) -> str:
        """搜索相关日志"""
        try:
            hostname = entities.get("hostname", [None])[0]
            if hostname:
                results = self.log_indexer.search_by_host(hostname, top_k=5)
            else:
                results = self.log_indexer.search(query, top_k=5)

            if not results:
                return ""
            return "\n".join(r.get("content", "")[:500] for r in results)
        except Exception as e:
            logger.warning("日志检索失败: {}", e)
            return ""

    def _run_diagnostics(self, entities: dict) -> str:
        """执行诊断脚本"""
        scripts = {
            "cpu": "check_cpu.sh",
            "内存": "check_memory.sh",
            "memory": "check_memory.sh",
            "磁盘": "check_disk.sh",
            "disk": "check_disk.sh",
        }
        outputs = []
        try:
            available = self.script_executor.list_scripts()
            for keyword, script in scripts.items():
                if keyword in str(entities).lower() and script in available:
                    result = self.script_executor.execute(script)
                    outputs.append(f"[{script}]\n{result['stdout']}")
            if not outputs:
                # 默认运行磁盘和内存检查
                for script in ["check_disk.sh", "check_memory.sh"]:
                    if script in available:
                        result = self.script_executor.execute(script)
                        outputs.append(f"[{script}]\n{result['stdout']}")
            return "\n".join(outputs)
        except Exception as e:
            logger.warning("脚本执行失败: {}", e)
            return ""

    @staticmethod
    def _format_rows(rows: list) -> str:
        """格式化数据库查询结果"""
        if not rows:
            return "查询结果为空"
        if len(rows) > 20:
            head = rows[:20]
            return "\n".join(str(r) for r in head) + f"\n...（共 {len(rows)} 行，仅显示前20行）"
        return "\n".join(str(r) for r in rows)
