import json
import logging
from typing import Any, Dict, List, Optional, Union

import httpx
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from src.config import KBChatConfig

logger = logging.getLogger(__name__)


class SearchDocsInput(BaseModel):
    query: str = Field(..., description="用户问题或检索关键词")


async def build_search_docs_tool(kb_names: Optional[Union[str, List[str]]] = None) -> StructuredTool:
    """
    创建 search_docs 工具
    """

    async def _search_docs(query: str) -> str:
        payload = {
            "query": query,
            "knowledge_base_name": kb_names,
            "top_k": 3,
            "score_threshold": 0.3,
            "file_name": "",
            "metadata": {},
            "enable_rerank": True,
            "graph_local_search_top_k": 3,
            "graph_global_search_top_k": 5,
        }

        url = f"{KBChatConfig.BASE_URL.rstrip('/')}/knowledge_base/search_docs"
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
            return json.dumps(response.json(), ensure_ascii=False)
        except Exception as e:
            logger.error("kb_chat search_docs failed: %s", e)
            return ""

    return StructuredTool.from_function(
        coroutine=_search_docs,
        name="search_docs",
        description="这是一个知识库文档的检索工具，输入是用户的问题或检索关键词，输出是一个包含相关文档信息的JSON字符串。当用户问题涉及领域知识查询、文档内容、术语解释时，优先调用该工具，检索相关的文档作为参考",
        args_schema=SearchDocsInput,
    )


async def build_kb_chat_tools(kb_names: Optional[Union[str, List[str]]] = None) -> List:
    tools = []
    try:
        search_docs_tool = await build_search_docs_tool(kb_names=kb_names)
        tools.append(search_docs_tool)
    except Exception as e:
        logger.warning("初始化 kb_chat 工具失败: %s" % str(e))
    return tools


search_docs_tool_prompt = """
[知识库检索工具 search_docs 使用规范]
- 你可以使用工具 search_docs 检索知识库。
- 当用户问题涉及领域知识查询、文档内容、术语解释时，优先调用该工具检索相关的文档再回答。
- 回答时要基于检索结果，不要编造事实，不要输出其它无关信息；若检索无结果，请明确说明。"
"""