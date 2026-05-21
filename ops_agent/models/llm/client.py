"""统一 LLM 客户端：DeepSeek（主）+ 阿里云百炼（备），支持流式/非流式"""
import asyncio
from typing import AsyncGenerator, Optional
from openai import AsyncOpenAI
from loguru import logger

from config.settings import settings
from ops_agent.utils.exceptions import LLMError, LLMTimeoutError, LLMAuthError


class DeepSeekEngine:
    """DeepSeek API 引擎（OpenAI 兼容）

    Args:
        api_key: API 密钥，默认从 settings 读取
        base_url: API 地址，默认从 settings 读取
        model_name: 模型名，默认从 settings 读取
    """

    def __init__(self, api_key: str = "", base_url: str = "", model_name: str = ""):
        self.client = AsyncOpenAI(
            api_key=api_key or settings.deepseek_api_key,
            base_url=base_url or settings.deepseek_base_url,
            timeout=60.0,
        )
        self.model = model_name or settings.deepseek_model

    async def chat(self, messages: list[dict], **kwargs) -> str:
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=kwargs.get("temperature", settings.llm_temperature),
                max_tokens=kwargs.get("max_tokens", settings.llm_max_tokens),
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            raise self._map_error(e)

    async def chat_stream(self, messages: list[dict], **kwargs) -> AsyncGenerator[str, None]:
        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=kwargs.get("temperature", settings.llm_temperature),
                max_tokens=kwargs.get("max_tokens", settings.llm_max_tokens),
                stream=True,
            )
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            raise self._map_error(e)

    def _map_error(self, e: Exception) -> Exception:
        msg = str(e)
        if "timeout" in msg.lower():
            return LLMTimeoutError(f"DeepSeek 请求超时: {msg}")
        if "401" in msg or "unauthorized" in msg.lower() or "authentication" in msg.lower():
            return LLMAuthError(f"DeepSeek API Key 无效: {msg}")
        return LLMError(f"DeepSeek 调用失败: {msg}")


class BailianEngine:
    """阿里云百炼引擎（DashScope）

    Args:
        api_key: API 密钥，默认从 settings 读取
        model_name: 模型名，默认从 settings 读取
    """

    def __init__(self, api_key: str = "", model_name: str = ""):
        import dashscope
        dashscope.api_key = api_key or settings.dashscope_api_key
        self.model = model_name or settings.bailian_model

    async def chat(self, messages: list[dict], **kwargs) -> str:
        try:
            from dashscope.aigc.generation import Generation
            response = await asyncio.to_thread(
                Generation.call,
                model=self.model,
                messages=messages,
                result_format="message",
                temperature=kwargs.get("temperature", settings.llm_temperature),
                max_tokens=kwargs.get("max_tokens", settings.llm_max_tokens),
            )
            if response.status_code == 200:
                return response.output.choices[0].message.content
            if response.status_code == 401:
                raise LLMAuthError(f"百炼 API Key 无效: {response.message}")
            raise LLMError(f"百炼调用失败: {response.message}")
        except (LLMError, LLMAuthError):
            raise
        except Exception as e:
            raise LLMError(f"百炼调用异常: {e}")

    async def chat_stream(self, messages: list[dict], **kwargs) -> AsyncGenerator[str, None]:
        try:
            from dashscope.aigc.generation import Generation
            responses = await asyncio.to_thread(
                Generation.call,
                model=self.model,
                messages=messages,
                result_format="message",
                temperature=kwargs.get("temperature", settings.llm_temperature),
                max_tokens=kwargs.get("max_tokens", settings.llm_max_tokens),
                stream=True,
                incremental_output=True,
            )
            for response in responses:
                if response.status_code == 200:
                    if response.output and response.output.choices:
                        content = response.output.choices[0].message.content
                        if content:
                            yield content
                elif response.status_code == 401:
                    raise LLMAuthError(f"百炼 API Key 无效: {response.message}")
                else:
                    raise LLMError(f"百炼流式调用失败: {response.message}")
        except (LLMError, LLMAuthError):
            raise
        except Exception as e:
            raise LLMError(f"百炼流式调用异常: {e}")


class UnifiedLLMClient:
    """统一 LLM 客户端，支持多引擎自动 fallback

    Args:
        engines: 可选引擎列表（按优先级），不传则从 settings 创建 DeepSeek + 百炼
    """

    def __init__(self, engines: Optional[list] = None):
        self.engines: list = []
        if engines:
            self.engines = engines
        else:
            self._init_engines()

    def _init_engines(self):
        self.engines = []
        if settings.deepseek_api_key and "your-" not in settings.deepseek_api_key:
            engine = DeepSeekEngine()
            self.engines.append(engine)
            logger.info("LLM 主引擎: DeepSeek ({})", settings.deepseek_model)
        else:
            logger.warning("DeepSeek API Key 未配置，跳过主引擎")

        if settings.dashscope_api_key and "your-" not in settings.dashscope_api_key:
            engine = BailianEngine()
            self.engines.append(engine)
            logger.info("LLM 备引擎: 百炼 ({})", settings.bailian_model)
        else:
            logger.warning("百炼 API Key 未配置，跳过备引擎")

        if not self.engines:
            logger.warning("未配置任何 LLM API Key，系统将无法回答问题")

    async def chat(self, messages: list[dict], **kwargs) -> str:
        """非流式对话，按引擎列表顺序自动 fallback"""
        if not self.engines:
            raise LLMError(
                "无可用 LLM 引擎。请先在「大模型配置」页面添加一个 LLM 提供商 "
                "(OpenAI 兼容接口或 DashScope)，或配置 .env 环境变量中的 API Key。"
            )
        last_error = None
        for engine in self.engines:
            try:
                return await engine.chat(messages, **kwargs)
            except (LLMTimeoutError, LLMAuthError) as e:
                logger.warning("引擎失败: {}，尝试下一个...", e)
                last_error = e
            except LLMError as e:
                logger.error("引擎错误: {}", e)
                last_error = e
        raise last_error or LLMError("所有 LLM 引擎均失败")

    async def chat_stream(self, messages: list[dict], **kwargs) -> AsyncGenerator[str, None]:
        """流式对话，按引擎列表顺序自动 fallback"""
        if not self.engines:
            raise LLMError(
                "无可用 LLM 引擎。请先在「大模型配置」页面添加一个 LLM 提供商 "
                "(OpenAI 兼容接口或 DashScope)，或配置 .env 环境变量中的 API Key。"
            )
        last_error = None
        for engine in self.engines:
            try:
                async for token in engine.chat_stream(messages, **kwargs):
                    yield token
                return
            except (LLMTimeoutError, LLMAuthError) as e:
                logger.warning("引擎流式失败: {}，尝试下一个...", e)
                last_error = e
            except LLMError as e:
                logger.error("引擎流式错误: {}", e)
                last_error = e
        raise last_error or LLMError("所有 LLM 引擎流式均失败")


# 全局单例
_llm_client: Optional[UnifiedLLMClient] = None


def get_llm_client() -> UnifiedLLMClient:
    global _llm_client
    if _llm_client is None:
        _llm_client = UnifiedLLMClient()
    return _llm_client
