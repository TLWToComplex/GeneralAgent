"""
Rerank utilities module.
Provides functions for reranking search results and query responses.
"""
import os
import requests
import logging
from typing import Optional, List

# 配置日志
logger = logging.getLogger(__name__)

# ========= 环境变量 =========
RERANK_URLS = os.getenv('RERANK_URLS', '').split(',')
RERANK_IDS = os.getenv('RERANK_IDS', '').split(',')
RERANK_API_KEYS = os.getenv('RERANK_API_KEYS', '').split(',')

# 默认使用第一个模型配置
DEFAULT_RERANK_ID = RERANK_IDS[0] if RERANK_IDS and RERANK_IDS[0] else ''
DEFAULT_RERANK_URL = RERANK_URLS[0] if RERANK_URLS and RERANK_URLS[0] else ''
DEFAULT_RERANK_API_KEY = RERANK_API_KEYS[0] if RERANK_API_KEYS and RERANK_API_KEYS[0] else ''

class RerankUtils:
    @staticmethod
    def rerank(text: str, documents: List[str]) -> List[str]:
        """
        对给定的文本和文档进行重排序
        :param text: 需要重排序的文本
        :param documents: 文档列表
        :return: 重排序后的文档列表
        """
        if not text or not documents:
            return []
        try:
            headers = {
                "Authorization": f"Bearer {DEFAULT_RERANK_API_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": DEFAULT_RERANK_ID,
                "query": text,
                "documents": documents
            }
            response = requests.post(DEFAULT_RERANK_URL, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            result = response.json()
            return result
        except Exception as e:
            logger.error(f"重排序失败: {str(e)}")
            return documents