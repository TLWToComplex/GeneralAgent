"""
Embedding utilities module.
Provides functions for generating and managing text embeddings.
"""
import os
import logging
import requests
from typing import Optional, List

# ========= 日志配置 =========
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
# logging.basicConfig(
#     level=getattr(logging, LOG_LEVEL, logging.INFO),
#     format='[%(asctime)s] %(levelname)s - %(message)s'
# )

# ========= 环境变量 =========
EMBEDDING_IDS  = os.getenv('EMBEDDING_IDS', '').split(',')
EMBEDDING_URLS = os.getenv('EMBEDDING_URLS', '').split(',')
EMBEDDING_API_KEYS = os.getenv('EMBEDDING_API_KEYS', '').split(',')

# 默认使用第一个模型配置
DEFAULT_EMBEDDING_ID = EMBEDDING_IDS[0] if EMBEDDING_IDS and EMBEDDING_IDS[0] else ''
DEFAULT_EMBEDDING_URL = EMBEDDING_URLS[0] if EMBEDDING_URLS and EMBEDDING_URLS[0] else ''
DEFAULT_EMBEDDING_API_KEY = EMBEDDING_API_KEYS[0] if EMBEDDING_API_KEYS and EMBEDDING_API_KEYS[0] else ''

class EmbeddingUtils:
    @staticmethod
    def get_embedding(text: str) -> Optional[List[float]]:
        """
        获取文本的 embedding 向量。
        :param text: 待向量化文本
        :return: embedding 向量或 None（失败时）
        """
        headers = {
            "Authorization": f"Bearer {DEFAULT_EMBEDDING_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": DEFAULT_EMBEDDING_ID,
            "input": text
        }

        try:
            logging.info("POST %s", DEFAULT_EMBEDDING_URL)
            logging.debug("Payload: %s", payload)

            resp = requests.post(
                DEFAULT_EMBEDDING_URL,
                json=payload,
                headers=headers,
                timeout=60
            )
            logging.info("HTTP %s %s", resp.status_code, resp.reason)
            resp.raise_for_status()

            data = resp.json().get("data", [])
            logging.debug("Response JSON: %s", resp.json())

            embedding = data[0]["embedding"] if data and isinstance(data[0], dict) else None
            logging.info("Embedding size: %s", len(embedding) if embedding else 0)
            return embedding

        except requests.exceptions.RequestException as e:
            logging.error("Request failed: %s", e)
            return None