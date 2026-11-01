"""
Tool agent engine module.
Provides the execution engine for tool agent operations and function calls.
"""
import os
import logging
from typing import Dict, Any, List
from src.core.tool_agent.tool_agent import ToolAgent

logger = logging.getLogger(__name__)

class ToolAgentEngine:
    _instance = None
    _agent = None
    _initialized = False

    @classmethod
    def get_instance(cls) -> 'ToolAgentEngine':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        if self._agent is None:
            llm_ids = os.getenv('LLM_IDS', '').split(',')
            llm_urls = os.getenv('LLM_URLS', '').split(',')
            llm_api_keys = os.getenv('LLM_API_KEYS', '').split(',')
            llm_max_tokens = os.getenv('LLM_MAX_TOKENS', '10000').split(',')
            tool_agent_model_id = os.getenv('TOOL_AGENT_MODEL', 'Qwen/Qwen2.5-7B-Instruct')

            # 查找匹配的模型索引，如果找不到则默认使用索引0
            model_indices = [i for i, model_id in enumerate(llm_ids) if model_id.strip() == tool_agent_model_id]
            model_index = model_indices[0] if model_indices else 0

            tool_agent_model_api_key = llm_api_keys[model_index].strip()
            tool_agent_model_base_url = llm_urls[model_index].strip()
            tool_agent_model_max_tokens = int(llm_max_tokens[model_index].strip())

            self._agent = ToolAgent(
                api_key=tool_agent_model_api_key, 
                model=tool_agent_model_id, 
                base_url=tool_agent_model_base_url, 
                max_tokens=tool_agent_model_max_tokens
            )

    async def ensure_initialized(self) -> None:
        """确保工具已加载完成"""
        if not self._initialized:
            folder = os.getenv('TOOL_FOLDER', 'ql_tools')
            logger.info(f"正在从文件夹 '{folder}' 加载工具...")
            await self._agent.load_tools(folder)
            self._initialized = True

    async def process_query(self, query: str, history: List[Dict[str, str]]) -> Dict[str, Any]:
        """处理用户查询"""
        await self.ensure_initialized()
        return await self._agent.run(query, history)

