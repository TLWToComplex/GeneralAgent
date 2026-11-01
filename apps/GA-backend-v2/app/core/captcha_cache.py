"""验证码缓存管理器。

基于进程内存存储验证码，支持 TTL 过期与容量上限，逻辑与老项目
``src/core/cache/captcha_cache.py`` 一致。
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class CaptchaCacheManager:
    """验证码缓存管理器。"""

    def __init__(self, default_ttl: int = 300, max_size: int = 1000) -> None:
        self._pool: Dict[str, Tuple[str, float]] = {}
        self._default_ttl = default_ttl
        self._max_size = max_size
        self._lock = threading.Lock()

    def set(self, captcha_id: str, code: str, ttl: Optional[int] = None) -> None:
        """存储验证码答案。"""
        expire_time = time.time() + (ttl if ttl is not None else self._default_ttl)
        with self._lock:
            if len(self._pool) >= self._max_size:
                oldest_key = min(self._pool, key=lambda k: self._pool[k][1])
                self._pool.pop(oldest_key, None)
                logger.info("验证码缓存已满，淘汰最早过期项: %s", oldest_key)
            self._pool[captcha_id] = (code, expire_time)
        logger.debug("验证码已存储: id=%s, ttl=%s", captcha_id, ttl or self._default_ttl)

    def get(self, captcha_id: str) -> Optional[str]:
        """读取验证码答案，不存在或已过期返回 ``None``（过期项顺带清除）。"""
        with self._lock:
            item = self._pool.get(captcha_id)
            if item is None:
                return None
            code, expire_time = item
            if time.time() > expire_time:
                del self._pool[captcha_id]
                return None
            return code

    def delete(self, captcha_id: str) -> None:
        """删除验证码（一次性使用：无论校验是否通过都删除）。"""
        with self._lock:
            self._pool.pop(captcha_id, None)

    def cleanup_expired(self) -> int:
        """清理所有过期验证码，返回清理条数。"""
        now = time.time()
        with self._lock:
            expired = [cid for cid, (_, expire_time) in self._pool.items() if now > expire_time]
            for cid in expired:
                self._pool.pop(cid, None)
        return len(expired)

    def __len__(self) -> int:
        return len(self._pool)