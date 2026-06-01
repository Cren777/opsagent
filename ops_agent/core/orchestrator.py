"""核心编排器：意图分类 → 路由分发 → 结果融合 → 流式输出"""
import asyncio
import re
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
from ops_agent.models.uploads.log_upload_service import LogUploadService
from ops_agent.models.troubleshooting.case_memory import IncidentCaseMemory


class Orchestrator:
    """系统核心编排器"""

    def __init__(self, llm_client: Optional[UnifiedLLMClient] = None):
        self.classifier = IntentClassifier(llm_client)
        self.router = TaskRouter()
        self.fusion = ResponseFusion(llm_client)

        self.kb = get_knowledge_base()
        self.text2sql = Text2SQLGenerator(llm_client=llm_client)
        self.log_indexer = LogIndexer()
        self.script_executor = ScriptExecutor()
        self.log_uploads = LogUploadService()
        self.case_memory = IncidentCaseMemory()

        self._register_handlers()

    def _register_handlers(self):
        """注册意图处理器"""
        self.router.register(IntentType.KNOWLEDGE_QUERY, self._handle_knowledge)
        self.router.register(IntentType.DATA_ANALYSIS, self._handle_data_analysis)
        self.router.register(IntentType.FAULT_TROUBLESHOOTING, self._handle_fault_troubleshooting)

    async def process(
        self,
        query: str,
        datasource_id: str = None,
        history: list[dict] = None,
        attachments: list[dict] = None,
    ) -> Dict[str, Any]:
        """非流式处理用户查询"""
        attachments = self._merge_log_attachments(
            attachments or [],
            self.log_uploads.resolve_mentioned_logs(query),
        )
        intent_result = await self.classifier.classify(query)
        intent = self._resolve_intent_for_attachments(intent_result.intent, attachments)
        result = await self.router.route(
            intent,
            query,
            intent_result.entities,
            datasource_id=datasource_id,
            history=history or [],
            attachments=attachments,
        )
        result["intent"] = intent.value
        return result

    async def process_stream(
        self,
        query: str,
        datasource_id: str = None,
        history: list[dict] = None,
        attachments: list[dict] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """流式处理用户查询，通过 SSE 事件逐步返回"""
        attachments = self._merge_log_attachments(
            attachments or [],
            self.log_uploads.resolve_mentioned_logs(query),
        )
        # Step 1: 意图识别
        intent_result = await self.classifier.classify(query)
        intent = self._resolve_intent_for_attachments(intent_result.intent, attachments)
        yield {"event": "intent", "data": {"type": intent.value}}

        # Step 2: 执行处理器
        result = await self.router.route(
            intent,
            query,
            intent_result.entities,
            datasource_id=datasource_id,
            history=history or [],
            attachments=attachments,
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
        done_data = {
            "intent": intent.value,
            "sources": result.get("sources", []),
            "sql": result.get("sql", ""),
        }
        if result.get("diagnostics"):
            done_data["diagnostics"] = result["diagnostics"]
        yield {"event": "done", "data": done_data}

    @staticmethod
    def _resolve_intent_for_attachments(intent: IntentType, attachments: list[dict] | None) -> IntentType:
        """Uploaded logs are explicit troubleshooting evidence, regardless of query wording."""
        if any(item.get("type") == "log" for item in attachments or []):
            return IntentType.FAULT_TROUBLESHOOTING
        return intent

    @staticmethod
    def _merge_log_attachments(explicit: list[dict], resolved: list[dict]) -> list[dict]:
        seen = {item.get("id") for item in explicit}
        merged = list(explicit)
        for item in resolved:
            if item.get("id") not in seen:
                merged.append(item)
                seen.add(item.get("id"))
        return merged

    async def _handle_knowledge(self, query: str, entities: dict, **kwargs) -> Dict[str, Any]:
        """处理知识查询"""
        context = self.kb.query(query)
        sources = self.kb.search(query, top_k=3)
        answer = await self.fusion.fuse_for_knowledge(query, context)
        return {
            "answer": answer,
            "sources": [{"title": s["title"], "file": s["source_file"]} for s in sources],
        }

    async def _handle_data_analysis(
        self,
        query: str,
        entities: dict,
        datasource_id: str = None,
        history: list[dict] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """处理数据分析查询"""
        try:
            ds = get_active_datasource()
            if ds is None:
                return {"answer": "错误：数据源未配置或连接失败，请在数据源配置页面检查。", "rows": []}

            if datasource_id:
                from ops_agent.models.tools.datasource_factory import get_datasource_by_id
                ds = get_datasource_by_id(datasource_id) or ds

            self.text2sql.schema_manager.set_datasource(ds)
            effective_query = self._augment_query_with_history_table(query, history or [])
            sql = await self.text2sql.generate(effective_query)
            rows = ds.execute_query(sql)
            results_text = self._format_rows(rows)
            answer = await self.fusion.fuse_for_data(query, results_text)
            return {"answer": answer, "sql": sql, "rows": rows}
        except Exception as e:
            logger.exception("数据分析处理失败")
            msg = str(e)
            if "inappropriate" in msg.lower():
                return {
                    "answer": (
                        "Text2SQL 请求被 LLM 内容审核拦截。"
                        "数据库 Schema 中的列名或样本数据可能触发了百炼的内容安全策略。\n\n"
                        "**建议**：请在「大模型配置」页面添加 DeepSeek 或其他 OpenAI 兼容接口作为主力模型。"
                    ),
                    "sql": "",
                    "rows": [],
                }
            return {
                "answer": f"数据分析处理失败: {msg}",
                "sql": "",
                "rows": [],
            }

    def _augment_query_with_history_table(self, query: str, history: list[dict]) -> str:
        """Attach the last referenced table when the user says only 'the table'."""
        table_names = self.text2sql.schema_manager.get_table_list()
        if any(table in query for table in table_names):
            return query

        last_table = self._find_last_table_from_history(history, table_names)
        if not last_table:
            return query

        if not re.search(r"\u8868|\u6570\u636e|\u8bb0\u5f55|\u4e00\u6761|\u968f\u673a|\u968f\u4fbf", query):
            return query

        return f"{query}\nTarget table: {last_table}"

    @staticmethod
    def _find_last_table_from_history(history: list[dict], table_names: list[str]) -> str:
        for item in reversed(history):
            content = str(item.get("content", ""))
            sql = str(item.get("sql", ""))
            combined = f"{sql}\n{content}"
            for table in sorted(table_names, key=len, reverse=True):
                if table in combined:
                    return table
        return ""

    async def _handle_fault_troubleshooting(self, query: str, entities: dict, **kwargs) -> Dict[str, Any]:
        """处理故障排查"""
        attachments = kwargs.get("attachments") or []
        upload_context = self.log_uploads.get_attachment_context(attachments)
        symptoms = self._collect_symptoms(query, entities, upload_context)
        case_match = self.case_memory.find_similar(query, symptoms=symptoms)
        if case_match:
            diagnostics = {
                "case_match": {
                    "case_id": case_match["case_id"],
                    "score": case_match["score"],
                    "root_cause": case_match.get("root_cause", ""),
                    "solution": case_match.get("solution", ""),
                },
                "evidence": case_match.get("evidence", []),
                "attachments": attachments,
            }
            return {
                "answer": self._format_case_match_answer(query, case_match),
                "diagnostics": diagnostics,
                "sources": [{"title": "历史故障案例", "file": case_match["case_id"]}],
            }

        # 并行获取多源信息
        knowledge_task = asyncio.create_task(
            asyncio.to_thread(self.kb.query, query)
        )
        log_task = asyncio.create_task(
            asyncio.to_thread(self._search_logs, query, entities)
        )
        script_task = asyncio.create_task(
            asyncio.to_thread(self._run_diagnostics, query, entities)
        )

        knowledge_context, log_context, script_output = await asyncio.gather(
            knowledge_task,
            log_task,
            script_task,
            return_exceptions=True,
        )
        knowledge_context = "" if isinstance(knowledge_context, Exception) else knowledge_context
        log_context = "" if isinstance(log_context, Exception) else log_context
        script_output = "" if isinstance(script_output, Exception) else script_output
        merged_log_context = "\n\n".join(part for part in [upload_context, log_context] if part)

        answer = await self.fusion.fuse_for_troubleshooting(
            question=query,
            knowledge_context=knowledge_context,
            db_results="",
            script_output=script_output,
            log_context=merged_log_context,
        )

        evidence = self._build_evidence(upload_context, log_context, script_output)
        if answer:
            try:
                self.case_memory.save_case(
                    query=query,
                    answer=answer,
                    symptoms=symptoms,
                    evidence=evidence,
                    status="auto_saved",
                )
            except Exception as e:
                logger.warning("保存故障案例失败: {}", e)

        return {
            "answer": answer,
            "diagnostics": {
                "symptoms": symptoms,
                "attachments": attachments,
                "evidence": evidence,
                "case_match": None,
            },
        }

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

    def _run_diagnostics(self, query: str, entities: dict) -> str:
        """执行诊断脚本"""
        scripts = {
            "cpu": "check_cpu.sh",
            "内存": "check_memory.sh",
            "memory": "check_memory.sh",
            "磁盘": "check_disk.sh",
            "disk": "check_disk.sh",
            "服务": "check_service.sh",
            "service": "check_service.sh",
            "nginx": "check_service.sh",
            "mysql": "check_service.sh",
            "redis": "check_service.sh",
        }
        outputs = []
        try:
            available = self.script_executor.list_scripts()
            target_text = f"{query} {entities}".lower()
            services = entities.get("service", []) if isinstance(entities, dict) else []
            for keyword, script in scripts.items():
                if keyword.lower() in target_text and script in available:
                    args = [services[0]] if script == "check_service.sh" and services else []
                    result = self.script_executor.execute(script, args=args)
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
    def _collect_symptoms(query: str, entities: dict, upload_context: str) -> list[str]:
        text = f"{query}\n{upload_context}".lower()
        symptoms = set()
        for key in [
            "cpu",
            "内存",
            "memory",
            "磁盘",
            "disk",
            "connection refused",
            "permission denied",
            "out of memory",
            "no space",
            "timeout",
            "timed out",
            "502",
            "503",
            "oom",
        ]:
            if key in text:
                symptoms.add(key)
        for value in entities.get("hostname", []) + entities.get("service", []) + entities.get("ip", []):
            symptoms.add(str(value).lower())
        return sorted(symptoms)

    @staticmethod
    def _build_evidence(upload_context: str, log_context: str, script_output: str) -> list[str]:
        evidence = []
        if upload_context:
            evidence.append("用户上传日志已解析并纳入诊断")
        if log_context:
            evidence.append("系统日志索引命中相关片段")
        if script_output:
            evidence.append("诊断脚本返回运行状态")
        return evidence

    @staticmethod
    def _format_case_match_answer(query: str, case_match: dict) -> str:
        return (
            "### 命中历史故障案例\n"
            f"当前问题与历史案例 `{case_match['case_id']}` 高度相似，匹配度 {case_match['score']:.0%}。\n\n"
            "### 历史处理方案\n"
            f"{case_match['answer']}\n\n"
            "### 本次建议确认\n"
            "请先核对本次日志中的关键报错、服务名和主机是否与历史案例一致；如果一致，可优先按历史方案处理。"
        )

    @staticmethod
    def _format_rows(rows: list) -> str:
        """格式化数据库查询结果"""
        if not rows:
            return "查询结果为空"
        if len(rows) > 20:
            head = rows[:20]
            return "\n".join(str(r) for r in head) + f"\n...（共 {len(rows)} 行，仅显示前20行）"
        return "\n".join(str(r) for r in rows)
